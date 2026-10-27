"""WP-LP3 experimental answer-conditioned soft-prefix path (SHADOW research only).

Unlike LP1/LP2's auxiliary cosine/InfoNCE, the *answer logits themselves*
consume the predicted prompt state through trainable prefix embeddings.
This is a differentiable mechanism, NOT evidence of learning utility, B1/B2
transfer, Age promotion or a deployed runtime route.
"""
import torch
from torch import nn
from torch.nn import functional as F

REVISION = 'v13-lp3-state-conditioned-prefix-v1'
ASSIGNMENTS = ('own', 'shift', 'zero')


class StateConditionedPrefix(nn.Module):
    """Frozen causal decoder + trainable prompt-state predictor and soft prefix.

    The state extractor sees only prompt tokens. Target tokens are appended
    solely for teacher-forced CE; logits at t-1 predict answer token t.
    """

    def __init__(self, base, prefix_tokens=2):
        super().__init__()
        if type(prefix_tokens) is not int or not 1 <= prefix_tokens <= 16:
            raise ValueError('Invalid soft-prefix token count')
        embedding = base.get_input_embeddings()
        if embedding is None or not hasattr(embedding, 'embedding_dim'):
            raise ValueError('Decoder needs token embeddings')
        hidden = int(embedding.embedding_dim)
        if hidden < 1:
            raise ValueError('Invalid decoder embedding width')
        self.base = base
        for param in self.base.parameters():
            param.requires_grad_(False)
        self.base.eval()
        self.hidden = hidden
        self.prefix_tokens = prefix_tokens
        self.predictor = nn.Sequential(nn.Linear(hidden, hidden), nn.Tanh())
        self.prefix_projector = nn.Linear(hidden, prefix_tokens * hidden)

    def train(self, mode=True):
        super().train(mode)
        self.base.eval()  # no stochastic teacher/base behavior, even while prefix trains
        return self

    def trainable_parameters(self):
        return list(self.predictor.parameters()) + list(self.prefix_projector.parameters())

    def _check_tokens(self, prompt_ids, answer_ids):
        if (not isinstance(prompt_ids, torch.Tensor) or not isinstance(answer_ids, torch.Tensor)
                or prompt_ids.dtype != torch.long or answer_ids.dtype != torch.long
                or prompt_ids.ndim != 2 or answer_ids.ndim != 2
                or prompt_ids.shape[0] != answer_ids.shape[0]
                or not prompt_ids.shape[0] or not prompt_ids.shape[1] or not answer_ids.shape[1]):
            raise ValueError('Nonempty same-batch int64 prompt and answer tokens required')
        vocab = self.base.get_input_embeddings().num_embeddings
        if (bool((prompt_ids < 0).any()) or bool((answer_ids < 0).any())
                or bool((prompt_ids >= vocab).any()) or bool((answer_ids >= vocab).any())):
            raise ValueError('Token ID outside frozen decoder vocabulary')

    def prompt_features(self, prompt_ids):
        if (not isinstance(prompt_ids, torch.Tensor) or prompt_ids.ndim != 2
                or prompt_ids.dtype != torch.long or not prompt_ids.shape[1]):
            raise ValueError('Invalid prompt tokens')
        with torch.no_grad():
            states = self.base(input_ids=prompt_ids, output_hidden_states=True,
                               use_cache=False).hidden_states
            feature = states[-1][:, -1, :].detach()
        if feature.ndim != 2 or feature.shape[1] != self.hidden:
            raise ValueError('Frozen prompt state width mismatch')
        return feature

    def answer_logits(self, prompt_ids, answer_ids, assignment='own', features=None):
        self._check_tokens(prompt_ids, answer_ids)
        if assignment not in ASSIGNMENTS:
            raise ValueError('Unknown assignment control')
        batch, prompt_len = prompt_ids.shape
        if assignment == 'shift' and batch < 2:
            raise ValueError('Shifted control requires at least two different items')
        if features is None:
            features = self.prompt_features(prompt_ids)
        if (not isinstance(features, torch.Tensor) or features.shape != (batch, self.hidden)
                or not bool(torch.isfinite(features).all())):
            raise ValueError('Nonfinite or mismatched prompt-only features')
        z = self.predictor(features.detach())
        if assignment == 'shift':
            z = z.roll(shifts=1, dims=0)
        prefix = self.prefix_projector(z).reshape(batch, self.prefix_tokens, self.hidden)
        if assignment == 'zero':
            prefix = torch.zeros_like(prefix)
        embed = self.base.get_input_embeddings()
        sequence = torch.cat((prefix, embed(prompt_ids), embed(answer_ids)), dim=1)
        # Frozen weights still pass gradients from answer CE back to the prefix.
        logits = self.base(inputs_embeds=sequence, use_cache=False).logits
        start = self.prefix_tokens + prompt_len - 1
        answer_logits = logits[:, start:start + answer_ids.shape[1], :]
        if answer_logits.shape[:2] != answer_ids.shape:
            raise ValueError('Answer-logit alignment mismatch')
        return answer_logits

    def answer_loss(self, prompt_ids, answer_ids, assignment='own', features=None):
        logits = self.answer_logits(prompt_ids, answer_ids, assignment, features)
        return F.cross_entropy(logits.reshape(-1, logits.shape[-1]), answer_ids.reshape(-1))
