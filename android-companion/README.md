# V14 Android Companion (experimental, OFF by default)

This is a separate native Android companion for the existing Termux runtime (which may
continue to be named `v13`). It is not installed by the V13 updater.

## Current scope

- One API-first capability: `launch_app`, with a user-visible per-action consent screen.
- Termux caller pairing is explicit and bound to the installed package signing-certificate
  SHA-256 digest.
- A local stop switch disables new requests; the default state is OFF.
- Receipts are signed with a non-exportable Android Keystore P-256 key.
- A successful `startActivity` dispatch is reported as
  `DISPATCHED_UNVERIFIED`, never as observed foreground state or a trusted WorldAction.
- UI observation, Accessibility, screen capture, tap/swipe/type/back, notifications as
  actions, and arbitrary shell execution remain OFF / not implemented.
- No network permission, remote server, hidden control, or automatic execution is present.

## Pairing and use

1. Install this companion separately only after explicit user approval.
2. Open it, pair the installed `com.termux` package by reviewing its signing-certificate
   fingerprint, then enable the companion.
3. The Termux-side client must pin the displayed public-key fingerprint before accepting
   receipts. A receipt's included key is never trusted by itself.
4. Each request appears as a pending item; the user opens the companion and approves or
   denies it. A request is never executed merely because it arrived over ContentProvider IPC.

The app is experimental and NOT_RELEASED. No Redmi installation or device behavior is
claimed by this source tree or its CI build.
