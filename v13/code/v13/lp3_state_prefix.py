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
        self._check_prompt(prompt_ids)
        with torch.no_grad():
            states = self.base(input_ids=prompt_ids, output_hidden_states=True,
                               use_cache=False).hidden_states
            feature = states[-1][:, -1, :].detach()
        if feature.ndim != 2 or feature.shape[1] != self.hidden:
            raise ValueError('Frozen prompt state width mismatch')
        return feature

    def _check_prompt(self, prompt_ids):
        if (not isinstance(prompt_ids, torch.Tensor) or prompt_ids.ndim != 2
                or prompt_ids.dtype != torch.long or not prompt_ids.shape[0]
                or not prompt_ids.shape[1]):
            raise ValueError('Nonempty int64 prompt tokens required')
        vocab = self.base.get_input_embeddings().num_embeddings
        if bool((prompt_ids < 0).any()) or bool((prompt_ids >= vocab).any()):
            raise ValueError('Prompt token outside frozen decoder vocabulary')
        context = getattr(self.base.config, 'max_position_embeddings', None)
        if context is not None and prompt_ids.shape[1] > context:
            raise ValueError('Prompt exceeds frozen decoder context')

    def _prefix_for(self, prompt_ids, assignment, features):
        if assignment not in ASSIGNMENTS:
            raise ValueError('Unknown assignment control')
        batch = prompt_ids.shape[0]
        if assignment == 'shift' and (batch < 2 or not bool((prompt_ids != prompt_ids[:1]).any())):
            raise ValueError('Shifted control requires at least two different prompts')
        supplied_features = features is not None
        if features is None:
            features = self.prompt_features(prompt_ids)
        if (not isinstance(features, torch.Tensor) or features.shape != (batch, self.hidden)
                or not features.is_floating_point() or not bool(torch.isfinite(features).all())):
            raise ValueError('Nonfinite or mismatched prompt-only features')
        # A public features= override must not bypass the prompt-only state
        # boundary: otherwise a caller could encode answer tokens in features.
        if supplied_features:
            reference = self.prompt_features(prompt_ids)
            if not torch.equal(features.detach().to(device=reference.device,
                                                    dtype=reference.dtype), reference):
                raise ValueError('Supplied features are not the frozen prompt-only state')
        features = features.detach().to(device=self.predictor[0].weight.device,
                                        dtype=self.predictor[0].weight.dtype)
        z = self.predictor(features)
        if assignment == 'shift':
            z = z.roll(shifts=1, dims=0)
        prefix = self.prefix_projector(z).reshape(batch, self.prefix_tokens, self.hidden)
        return torch.zeros_like(prefix) if assignment == 'zero' else prefix

    def answer_logits(self, prompt_ids, answer_ids, assignment='own', features=None):
        self._check_tokens(prompt_ids, answer_ids)
        batch, prompt_len = prompt_ids.shape
        context = getattr(self.base.config, 'max_position_embeddings', None)
        if context is not None and self.prefix_tokens + prompt_len + answer_ids.shape[1] > context:
            raise ValueError('Teacher-forced sequence exceeds frozen decoder context')
        prefix = self._prefix_for(prompt_ids, assignment, features)
        embed = self.base.get_input_embeddings()
        sequence = torch.cat((prefix, embed(prompt_ids), embed(answer_ids)), dim=1)
        # Frozen weights still pass gradients from answer CE back to the prefix.
        logits = self.base(inputs_embeds=sequence, use_cache=False).logits
        start = self.prefix_tokens + prompt_len - 1
        answer_logits = logits[:, start:start + answer_ids.shape[1], :]
        if answer_logits.shape[:2] != answer_ids.shape:
            raise ValueError('Answer-logit alignment mismatch')
        return answer_logits

    def next_token_logits(self, prompt_ids, assignment='own', features=None):
        """Target-free inference path: first next-token logits consume predicted state."""
        self._check_prompt(prompt_ids)
        context = getattr(self.base.config, 'max_position_embeddings', None)
        if context is not None and self.prefix_tokens + prompt_ids.shape[1] > context:
            raise ValueError('Inference sequence exceeds frozen decoder context')
        prefix = self._prefix_for(prompt_ids, assignment, features)
        embed = self.base.get_input_embeddings()
        seq = torch.cat((prefix, embed(prompt_ids)), dim=1)
        return self.base(inputs_embeds=seq, use_cache=False).logits[:, -1, :]

    @torch.no_grad()
    def greedy(self, prompt_ids, max_new_tokens=8, assignment='own'):
        """Bounded synthetic decoder; no teacher-forced target or live authority."""
        self._check_prompt(prompt_ids)
        if type(max_new_tokens) is not int or not 1 <= max_new_tokens <= 32:
            raise ValueError('Invalid generation token budget')
        context = getattr(self.base.config, 'max_position_embeddings', None)
        if context is not None and self.prefix_tokens + prompt_ids.shape[1] + max_new_tokens > context:
            raise ValueError('Generation exceeds frozen decoder context')
        features = self.prompt_features(prompt_ids)
        prefix = self._prefix_for(prompt_ids, assignment, features)
        embed = self.base.get_input_embeddings()
        generated = prompt_ids
        for _ in range(max_new_tokens):
            seq = torch.cat((prefix, embed(generated)), dim=1)
            token = self.base(inputs_embeds=seq, use_cache=False).logits[:, -1, :].argmax(dim=-1, keepdim=True)
            generated = torch.cat((generated, token), dim=1)
        return generated[:, prompt_ids.shape[1]:]

    def answer_loss(self, prompt_ids, answer_ids, assignment='own', features=None):
        logits = self.answer_logits(prompt_ids, answer_ids, assignment, features)
        return F.cross_entropy(logits.reshape(-1, logits.shape[-1]), answer_ids.reshape(-1))

    def _prefix_from_source(self, target_prompt_ids, source_prompt_ids):
        """Research-only explicit wrong-source control; never accepts raw features.

        The caller is responsible for preregistering source prompts that contain
        no target answers. This API proves source provenance only as token input.
        """
        self._check_prompt(target_prompt_ids)
        self._check_prompt(source_prompt_ids)
        if (source_prompt_ids.shape[0] != target_prompt_ids.shape[0]
                or source_prompt_ids.device != target_prompt_ids.device):
            raise ValueError('Source and target prompt batch/device mismatch')
        if torch.equal(source_prompt_ids, target_prompt_ids):
            raise ValueError('Wrong-source control requires a distinct source prompt')
        features = self.prompt_features(source_prompt_ids)
        features = features.detach().to(device=self.predictor[0].weight.device,
                                        dtype=self.predictor[0].weight.dtype)
        z = self.predictor(features)
        return self.prefix_projector(z).reshape(
            target_prompt_ids.shape[0], self.prefix_tokens, self.hidden)

    def answer_logits_from_source(self, target_prompt_ids, source_prompt_ids, answer_ids):
        """Teacher-forced CE for a source state extracted from separate prompt tokens."""
        self._check_tokens(target_prompt_ids, answer_ids)
        context = getattr(self.base.config, 'max_position_embeddings', None)
        if (context is not None and self.prefix_tokens + target_prompt_ids.shape[1]
                + answer_ids.shape[1] > context):
            raise ValueError('Teacher-forced source-control sequence exceeds decoder context')
        prefix = self._prefix_from_source(target_prompt_ids, source_prompt_ids)
        embed = self.base.get_input_embeddings()
        seq = torch.cat((prefix, embed(target_prompt_ids), embed(answer_ids)), dim=1)
        logits = self.base(inputs_embeds=seq, use_cache=False).logits
        start = self.prefix_tokens + target_prompt_ids.shape[1] - 1
        answer_logits = logits[:, start:start + answer_ids.shape[1], :]
        if answer_logits.shape[:2] != answer_ids.shape:
            raise ValueError('Source-control answer alignment mismatch')
        return answer_logits

    def answer_loss_from_source(self, target_prompt_ids, source_prompt_ids, answer_ids):
        logits = self.answer_logits_from_source(target_prompt_ids, source_prompt_ids, answer_ids)
        return F.cross_entropy(logits.reshape(-1, logits.shape[-1]), answer_ids.reshape(-1))

    def next_token_logits_from_source(self, target_prompt_ids, source_prompt_ids):
        """Target-free logits; wrong source may have different token length."""
        self._check_prompt(target_prompt_ids)
        context = getattr(self.base.config, 'max_position_embeddings', None)
        if context is not None and self.prefix_tokens + target_prompt_ids.shape[1] > context:
            raise ValueError('Source-control inference exceeds decoder context')
        prefix = self._prefix_from_source(target_prompt_ids, source_prompt_ids)
        embed = self.base.get_input_embeddings()
        seq = torch.cat((prefix, embed(target_prompt_ids)), dim=1)
        return self.base(inputs_embeds=seq, use_cache=False).logits[:, -1, :]

    @torch.no_grad()
    def greedy_from_source(self, target_prompt_ids, source_prompt_ids, max_new_tokens=8):
        """Bounded target-free wrong-source generation; research-only."""
        self._check_prompt(target_prompt_ids)
        if type(max_new_tokens) is not int or not 1 <= max_new_tokens <= 32:
            raise ValueError('Invalid generation token budget')
        context = getattr(self.base.config, 'max_position_embeddings', None)
        if (context is not None and self.prefix_tokens + target_prompt_ids.shape[1]
                + max_new_tokens > context):
            raise ValueError('Source-control generation exceeds decoder context')
        prefix = self._prefix_from_source(target_prompt_ids, source_prompt_ids)
        embed = self.base.get_input_embeddings()
        generated = target_prompt_ids
        for _ in range(max_new_tokens):
            seq = torch.cat((prefix, embed(generated)), dim=1)
            token = self.base(inputs_embeds=seq, use_cache=False).logits[:, -1, :].argmax(
                dim=-1, keepdim=True)
            generated = torch.cat((generated, token), dim=1)
        return generated[:, target_prompt_ids.shape[1]:]
