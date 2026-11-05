"""Isolated candidate for explicitly requested Age plasticity reopening.

This module is not imported by the live runtime.  It delegates the existing
error, stability and noise calculations to the supplied AgeControl and only
enforces the documented novelty floors when the caller explicitly requests a
new domain or modality.  It grants no rights, changes no state and does not
enable learning.  Runtime integration requires a separate review and evidence.
"""


def plasticity_candidate(
    controller,
    capability="system",
    novel_domain=False,
    repeated_errors=0,
    new_modality=False,
):
    """Return the existing budget with floors for explicitly signaled novelty.

    A new modality opens plasticity to 1.0; a novel domain has a floor of 0.8.
    When neither flag is true the original result is returned exactly, so the
    controller's repeated-error and demotion-hold logic is preserved.
    """
    if type(novel_domain) is not bool or type(new_modality) is not bool:
        raise ValueError("novel_domain and new_modality must be explicit booleans")
    budget = controller.plasticity(
        capability,
        novel_domain=novel_domain,
        repeated_errors=repeated_errors,
        new_modality=new_modality,
    )
    if new_modality:
        return max(budget, 1.0)
    if novel_domain:
        return max(budget, 0.8)
    return budget
