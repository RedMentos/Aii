import unittest
import torch

from latent_cache_tiny import DenseKVAdapter, TinyDecoder, TinySpec, run_experiment


class LatentCacheTinyTests(unittest.TestCase):
    def test_cross_geometry_adapter_shapes_and_gradients(self):
        sender_spec = TinySpec(2, 24, 4)
        receiver_spec = TinySpec(3, 32, 4)
        sender = TinyDecoder(sender_spec)
        receiver = TinyDecoder(receiver_spec)
        tokens = torch.tensor([[0, 4, 13, 1, 5]], dtype=torch.long)
        _, sender_cache = sender(tokens, use_cache=True)
        _, receiver_cache = receiver(tokens, use_cache=True)
        adapter = DenseKVAdapter(sender_spec, receiver_spec)
        mapped = adapter(sender_cache)
        self.assertEqual(len(mapped), receiver_spec.layers)
        for (k, v), (rk, rv) in zip(mapped, receiver_cache):
            self.assertEqual(k.shape, rk.shape)
            self.assertEqual(v.shape, rv.shape)
        loss = sum((k-rk).square().mean() + (v-rv).square().mean()
                   for (k, v), (rk, rv) in zip(mapped, receiver_cache))
        loss.backward()
        self.assertTrue(any(p.grad is not None and p.grad.abs().sum() > 0 for p in adapter.parameters()))

    def test_mismatched_sender_layer_count_rejected(self):
        adapter = DenseKVAdapter(TinySpec(2, 24, 4), TinySpec(3, 32, 4))
        with self.assertRaises(ValueError):
            adapter([])

    def test_end_to_end_latent_injection_beats_negative_controls_and_restarts(self):
        result = run_experiment(seed=13, train_n=512, test_n=128,
                                model_steps=320, phase1_steps=360, phase2_steps=180)
        self.assertEqual(result["proof_level"], "LOCAL_LINUX_TINY_MODEL_PROOF_NOT_PRODUCT_NATIVE")
        self.assertLess(result["adapter"]["heldout_reconstruction_mse_after_phase1"],
                        result["adapter"]["initial_heldout_reconstruction_mse"])
        self.assertGreater(result["adapter"]["total_parameter_delta_l2"], 0.0)
        self.assertGreater(result["adapter"]["max_phase1_gradient_norm"], 0.0)
        scores = result["heldout_accuracy"]
        self.assertGreater(scores["latent_cache"], scores["no_message"] + 0.20)
        self.assertGreater(scores["latent_cache"], scores["shuffled_sender_cache"] + 0.20)
        self.assertGreater(scores["latent_cache"], scores["random_adapter"] + 0.20)
        self.assertLess(result["restart_max_abs_logit_delta"], 1.0e-6)


if __name__ == "__main__":
    unittest.main()
