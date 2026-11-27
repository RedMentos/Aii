# V14 Android Companion (experimental, OFF by default)

This is a separate native Android companion for the existing Termux runtime (which may
continue to be named `v13`). It is not installed or updated by the V13 updater.

## Implemented companion capabilities

- `launch_app`: API-first app launch with a visible per-action consent screen.
  A signed receipt attests the companion's dispatch/consent result only; it is not
  proof that the app reached the foreground or that the device state was observed.
- `open_url`: HTTPS-only `ACTION_VIEW` with `CATEGORY_BROWSABLE` and a visible
  per-action approval screen. It launches the user's browser; it is not an agent
  HTTP client or arbitrary network-egress tool. The receipt proves dispatch only,
  not that a page loaded or that the browser reached a particular state. The full
  URL is redacted to its host after the signed receipt is durable.
- `screen_capture`: one-shot full-display MediaProjection frame capture. The user
  starts capture inside this app and separately approves Android's system
  MediaProjection prompt for that session. The frame is bounded, signed by the
  paired companion key, and exposed through a one-use ContentProvider pipe.
- Termux pairing is explicit and bound to the installed package signing-certificate
  SHA-256 digest. The public key must be compared and explicitly pinned in Termux.
- The companion's local stop switch disables new requests. Default state is OFF.
- The companion has no tap, swipe, type, back, AccessibilityService, arbitrary
  shell, or direct HTTP/network-egress capability. Those remain OFF / not implemented.
  `open_url` only delegates a user-approved HTTPS target to Android's browser intent.

## Runtime data boundary

- The normal Runtime consumes a frame only when a one-shot frame is already ready
  under the signed companion receipt and live per-session OS consent.
- The outer UIObservationLease and inner A5 source scope remain active through the
  same turn's B1/B2 offers and C3 generation. Revocation cancels the owning turn.
- The Termux Runtime does not persist raw screenshot bytes or the derived A5
  PerceptPacket. It retains only content-free binding metadata in the turn record;
  the visual summary is transient and is not added to saved context or the output
  adapter's learning input.
- The frame's low-level RAW-EYE features are not OCR or object recognition and
  grant no action, truth, or learning authority.
- A signed action receipt is published to the shared space as a source-bound
  `CONTROL_ONLY` C5 signal for the next turn. It is not a device observation,
  reward, T8 transition, trained latent, or weight-update permission.

## Pairing and use

1. Install this companion separately only after explicit user approval.
2. Open it, pair the installed `com.termux` package by reviewing its signing-certificate
   fingerprint, then explicitly enable the companion.
3. In Termux, compare the displayed key fingerprint and pin it with the local
   operator command. A receipt's included key is never trusted by itself.
4. To capture a screen, start the capture flow in the companion and approve the
   Android system MediaProjection prompt. The next non-direct Runtime turn may
   consume that single ready frame; no capture is started automatically.
5. `:android frame-status` reports signed one-shot frame metadata without
   consuming the frame bytes or nonce.
6. `:android open-url https://example.com/path --confirm` proposes browser
   navigation. The local Termux operator must confirm and the companion shows a
   separate Android consent screen; the action remains OFF unless pairing and the
   companion enable switch are active.

The app is experimental and NOT_RELEASED. CI builds and emulator tests are not
Redmi installation, MediaProjection permission, or real-device proof.
