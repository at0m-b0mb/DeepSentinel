"""Educational content — how deepfakes work, attack surface, and detection science.

All code snippets are simplified for teaching purposes only.
FOR EDUCATIONAL AND RESEARCH USE ONLY.
"""

SECTIONS: dict[str, dict] = {

# ── 1. Introduction ───────────────────────────────────────────────────────────
"intro": {
    "title": "What Are Deepfakes?",
    "code": None,
    "content": """
<h2>What Are Deepfakes?</h2>
<p>
<b>Deepfakes</b> are synthetic media — images, videos, or audio — where a person's
likeness is digitally altered or replaced using deep learning. The word combines
<i>deep learning</i> and <i>fake</i>.
</p>

<h3>A Brief History</h3>
<ul>
  <li><b>2017</b> — A Reddit user published an encoder-decoder face-swap script.
      Within weeks, thousands of videos circulated online.</li>
  <li><b>2018</b> — FaceForensics++ dataset released; the academic detection race began.</li>
  <li><b>2019–2022</b> — GAN-based methods raised realism to near-undetectable levels.
      Diffusion models entered the picture.</li>
  <li><b>2023–present</b> — Voice cloning + video synthesis enable fully synthetic
      impersonations in real time. Laws and treaties respond worldwide.</li>
</ul>

<h3>Three Main Categories</h3>
<ul>
  <li><b>Face Swap</b> — Replaces one person's face onto another's body in video
      (original deepfake technique). Tools: DeepFaceLab, FaceSwap, SimSwap.</li>
  <li><b>Face Reenactment</b> — Drives a target's expressions using a source actor's
      movements without replacing geometry. Tools: FOMM, SadTalker.</li>
  <li><b>Fully Synthetic</b> — Generates a completely artificial face that never
      existed. Tools: StyleGAN2/3, Stable Diffusion, Midjourney.</li>
</ul>

<h3>Why This Matters (Threat Model)</h3>
<ul>
  <li>Non-consensual intimate imagery (NCII / "deepfake porn") — primary misuse vector</li>
  <li>Political disinformation — fake statements attributed to world leaders</li>
  <li>Fraud — bypassing KYC/video verification for bank accounts</li>
  <li>Blackmail and reputational harm targeting private individuals</li>
  <li>Evidence fabrication in legal proceedings</li>
</ul>

<h3>Legitimate Uses (Why Detection Matters)</h3>
<ul>
  <li>Special effects and post-production in film / VFX</li>
  <li>Historical figure recreation for education (museums, documentaries)</li>
  <li>Accessibility — dubbing faces while preserving lip sync</li>
  <li>Privacy protection: anonymization in research footage</li>
</ul>
<p>
<i>Use the <b>Analyze Media</b> and <b>Live Detection</b> tabs to identify whether
content you encounter may be synthetically generated.</i>
</p>
""",
},

# ── 2. The Original Algorithm ─────────────────────────────────────────────────
"algorithm": {
    "title": "The Original Algorithm",
    "content": """
<h2>The 2017 Autoencoder Face-Swap Algorithm</h2>
<p>
The original deepfake used a simple idea: two autoencoders sharing a single encoder.
The insight is that <b>faces share a universal latent structure</b> (pose, expression,
lighting) — only the surface texture differs per person.
</p>

<h3>Architecture</h3>
<pre>
  Training:
  ┌──────────┐     ┌────────────────┐     ┌─────────────┐
  │  Face A  │────▶│                │────▶│  Decoder A  │────▶ Recon A
  └──────────┘     │  SHARED        │     └─────────────┘
                   │  ENCODER       │
  ┌──────────┐     │  (one copy,    │     ┌─────────────┐
  │  Face B  │────▶│  shared loss)  │────▶│  Decoder B  │────▶ Recon B
  └──────────┘     └────────────────┘     └─────────────┘

  Inference  (swap A→B):
  Face A  ──▶  ENCODER  ──▶  Decoder B  ──▶  Person A's pose, Person B's face
</pre>

<h3>Why It Works</h3>
<p>Because the encoder is shared and trained on <i>both</i> identities, it must learn
a representation that captures pose and expression independently of identity.
Decoder B maps that representation into person B's appearance.</p>

<h3>Full Pipeline Steps</h3>
<ul>
  <li><b>Step 1 — Data collection:</b> Hundreds of aligned face images per person.</li>
  <li><b>Step 2 — Preprocessing:</b> 68-point landmark alignment; random augmentation.</li>
  <li><b>Step 3 — Training:</b> 100k–500k iterations on GPU. Loss = L1 + perceptual.</li>
  <li><b>Step 4 — Inference:</b> Detect face → encode → decode with wrong decoder → blend back.</li>
  <li><b>Step 5 — Post-processing:</b> Colour correction, sharpening, temporal smoothing.</li>
</ul>
<p>See the <b>code panel below</b> for a simplified PyTorch implementation of the
core architecture. A <i>working</i> system additionally requires days of GPU training
and thousands of source images — this snippet is strictly educational.</p>
""",
    "code": '''\
# +=======================================================================+
# |  DEEPFAKE AUTOENCODER -- SIMPLIFIED EDUCATIONAL IMPLEMENTATION        |
# |  FOR LEARNING PURPOSES ONLY. NOT FOR MISUSE.                          |
# |  Based on: original Reddit 2017 algorithm (public domain concept)     |
# +=======================================================================+

import torch, torch.nn as nn, torch.nn.functional as F


class ConvBlock(nn.Module):
    # Conv -> LeakyReLU (with optional stride-2 downsample)
    def __init__(self, in_ch, out_ch, downsample=True):
        super().__init__()
        self.conv = nn.Conv2d(in_ch, out_ch, 5,
                              stride=2 if downsample else 1, padding=2)
        self.act  = nn.LeakyReLU(0.1, inplace=True)
    def forward(self, x): return self.act(self.conv(x))


class UpBlock(nn.Module):
    # Bilinear upsample x2 -> Conv  (avoids transposed-conv checkerboard)
    def __init__(self, in_ch, out_ch):
        super().__init__()
        self.up   = nn.Upsample(scale_factor=2, mode='bilinear', align_corners=False)
        self.conv = nn.Conv2d(in_ch, out_ch, 3, padding=1)
        self.act  = nn.LeakyReLU(0.1, inplace=True)
    def forward(self, x): return self.act(self.conv(self.up(x)))


# -- Shared Encoder  -------------------------------------------------------
# Maps face -> compact latent z.
# ONE instance, updated by gradients from BOTH autoencoders.
# Input  : (B, 3, 64, 64)
# Output : (B, 512)   <-- pose + expression, identity-agnostic
class SharedEncoder(nn.Module):
    def __init__(self, z=512):
        super().__init__()
        self.net = nn.Sequential(
            ConvBlock(  3,  64),   # 64 -> 32
            ConvBlock( 64, 128),   # 32 -> 16
            ConvBlock(128, 256),   # 16 ->  8
            ConvBlock(256, 512),   #  8 ->  4
        )
        self.fc = nn.Linear(512 * 4 * 4, z)
    def forward(self, x): return self.fc(self.net(x).flatten(1))


# -- Person-Specific Decoder (one per identity)  ---------------------------
# Maps shared latent z -> face image in *this person's* appearance.
# Train decoder_A on person A images.
# Train decoder_B on person B images.
# Input  : (B, 512)
# Output : (B, 3, 64, 64)
class PersonDecoder(nn.Module):
    def __init__(self, z=512):
        super().__init__()
        self.fc  = nn.Linear(z, 512 * 4 * 4)
        self.net = nn.Sequential(
            UpBlock(512, 256),
            UpBlock(256, 128),
            UpBlock(128,  64),
            UpBlock( 64,  32),
        )
        self.out = nn.Conv2d(32, 3, 1)
    def forward(self, z):
        h = self.fc(z).view(-1, 512, 4, 4)
        return torch.sigmoid(self.out(self.net(h)))


# ── Training (sketch)  ────────────────────────────────────────────────────
encoder   = SharedEncoder()
decoder_A = PersonDecoder()   # learns to reconstruct person A
decoder_B = PersonDecoder()   # learns to reconstruct person B

all_params  = (list(encoder.parameters()) +
               list(decoder_A.parameters()) +
               list(decoder_B.parameters()))
optimizer   = torch.optim.Adam(all_params, lr=5e-5, betas=(0.5, 0.999))

def train_step(face_a, face_b):
    optimizer.zero_grad()
    loss  = F.l1_loss(decoder_A(encoder(face_a)), face_a)   # reconstruct A
    loss += F.l1_loss(decoder_B(encoder(face_b)), face_b)   # reconstruct B
    loss.backward()
    optimizer.step()

# -- Inference: THE FACE SWAP  --------------------------------------------
def swap_a_to_b(face_a):
    with torch.no_grad():
        z = encoder(face_a)      # encode person A's pose/expression
        return decoder_B(z)      # decode as person B's face  <-- deepfake

# NOTE: A production pipeline also needs landmark alignment, Poisson blending,
# colour correction, temporal smoothing, and super-resolution.
# Training requires ~100k iterations on GPU + thousands of source images.
''',
},

# ── 3. Modern Methods ─────────────────────────────────────────────────────────
"modern": {
    "title": "Modern Methods",
    "code": None,
    "content": """
<h2>Modern Deepfake Methods (2019 – Present)</h2>
<p>The original autoencoder is largely superseded by GAN and diffusion systems
that produce far more realistic results with fewer source images.</p>

<h3>GAN-Based Face Swap</h3>
<ul>
  <li><b>SimSwap (2020)</b> — Identity injection via AdaIN; preserves target attributes
      while transplanting source identity. Real-time capable.</li>
  <li><b>FaceShifter (2020)</b> — Two-stage: coarse swap + occlusion-aware refinement.
      Handles glasses, hair, extreme poses.</li>
  <li><b>HifiFace (2021)</b> — 3D shape-aware identity injection; stable under large
      head rotations.</li>
  <li><b>InSwapper / InsightFace (2023)</b> — Near real-time at HD resolution.</li>
</ul>

<h3>Diffusion-Based Synthesis</h3>
<ul>
  <li><b>IP-Adapter + Stable Diffusion</b> — Face identity injected into any generated
      scene via cross-attention. Single reference image suffices.</li>
  <li><b>InstantID / PhotoMaker (2024)</b> — Output indistinguishable from professional
      photography from a single selfie.</li>
</ul>

<h3>Full Reenactment (No Source Actor Needed)</h3>
<ul>
  <li><b>First Order Motion Model (FOMM)</b> — Drives any portrait using keypoint
      trajectories from a driving video. Zero-shot.</li>
  <li><b>SadTalker / SyncTalk (2023)</b> — Audio-driven talking head from one photo.</li>
  <li><b>Deep Live Cam (2024)</b> — Real-time face swap through webcam, open source.</li>
</ul>

<h3>Voice Deepfakes (Combined Threat)</h3>
<ul>
  <li><b>VALL-E (2023)</b> — 3-second voice clone for any speaker.</li>
  <li><b>ElevenLabs / Tortoise-TTS</b> — Commercial and open-source voice cloning.</li>
  <li>Combined with video deepfakes: fully synthetic AI personas capable of
      real-time conversation, used in vishing and business-email-compromise scams.</li>
</ul>

<h3>The Detection Arms Race</h3>
<p>Each generation leaves <i>different artifacts</i>. Detectors trained on one generation
often fail on the next. DeepSentinel's heuristic approach looks for <b>fundamental
signal-processing artifacts</b> — FFT periodicity, SRM noise statistics, face boundary
inconsistency — which are more robust across generations than learned classifiers.</p>
""",
},

# ── 4. Detection Science ──────────────────────────────────────────────────────
"detection": {
    "title": "Detection Science",
    "code": None,
    "content": """
<h2>How Deepfake Detection Works</h2>
<p>DeepSentinel implements three families of detector: <b>signal/forensic</b>,
<b>neural network</b>, and <b>biometric consistency</b>.</p>

<h3>1. FFT Frequency Domain Analysis</h3>
<p>GAN upsampling via transposed convolutions produces periodic <b>checkerboard
artifacts</b> visible as spikes in the 2D FFT spectrum. Real camera images have
smooth, isotropic frequency distributions.</p>
<pre>
Real image FFT:      GAN image FFT:
· · · · ·            · · ↑ · ↑ ·
· · · · ·            · · · · · ·
· · ★ · ·   vs.      · · ★ · · ·   (★ = DC)
· · · · ·            · ← · → · ·
· · · · ·            · · ↓ · ↓ ·
 (smooth)            (regular spikes at stride frequencies)
</pre>

<h3>2. Error Level Analysis (ELA)</h3>
<p>Re-compressing at a known JPEG quality and diffing against the original reveals
regions saved at a different quality level — a composited face will show a
discontinuity at its boundary.</p>

<h3>3. Face Geometry + Boundary Analysis</h3>
<p>Haar cascade detection finds faces; eye positions are cross-checked against
anthropometric distributions. The Laplacian sharpness drop at the face perimeter
reveals Poisson blending seams common to face-swap pipelines.</p>

<h3>4. SRM Noise Residual Analysis</h3>
<p>Steganalysis Rich Model filters extract high-frequency pixel noise. Authentic
photos carry CMOS sensor noise. Synthetic faces are either over-smooth (diffusion)
or periodically structured (GAN upsampling). Kurtosis of residuals flags both.</p>

<h3>5. MesoNet Neural Network</h3>
<p>A 156K-parameter CNN trained on FaceForensics++ exploits mesoscopic texture
artifacts that appear when generators fail to model fine skin detail. Requires
pretrained weights (download from the MesoNet GitHub repo).</p>

<h3>Limitations</h3>
<ul>
  <li>Heuristic methods catch <b>low-to-medium quality</b> deepfakes. SOTA diffusion
      output can evade all current public detectors.</li>
  <li>Social-media compression (H.264, JPEG) destroys frequency artifacts.</li>
  <li>MesoNet (2018) may not generalise to 2024-era diffusion fakes without retraining.</li>
  <li><b>Never base a consequential decision solely on automated detection.</b></li>
</ul>
""",
},

# ── 5. Legal & Ethical ────────────────────────────────────────────────────────
"legal": {
    "title": "Legal & Ethical Context",
    "code": None,
    "content": """
<h2>Legal &amp; Ethical Context</h2>

<h3>Key Legislation</h3>
<ul>
  <li><b>UK — Online Safety Act 2023:</b> Criminalises sharing NCII deepfakes (up to
      2 years). Creating deepfakes without consent added in Criminal Justice Bill 2024.</li>
  <li><b>US — DEFIANCE Act 2024:</b> Federal civil claim for NCII deepfakes. Dozens of
      states have complementary criminal statutes.</li>
  <li><b>EU — AI Act 2024:</b> Mandatory watermarking of AI-generated content; bans
      certain biometric categorisation; heavy fines for providers.</li>
  <li><b>China — Synthetic Content Regulations 2022:</b> Mandatory labelling; consent
      required for face generation.</li>
</ul>

<h3>Ethical Principles for Researchers</h3>
<ul>
  <li><b>Consent first</b> — Never create synthetic media of real people without
      explicit, informed consent.</li>
  <li><b>Dual-use awareness</b> — Detection research can be repurposed for evasion.
      Publish responsibly; coordinate before releasing code.</li>
  <li><b>Provenance disclosure</b> — Label all AI-generated content. Use C2PA
      content credentials or watermarking tools.</li>
  <li><b>Report misuse</b> — Report NCII deepfakes to the hosting platform and
      NCMEC (US), IWF (UK), or local authorities.</li>
</ul>

<h3>Responsible Disclosure</h3>
<ul>
  <li>Share detection datasets and benchmarks so the community builds better tools.</li>
  <li>Avoid publishing evasion techniques without first coordinating with detector
      authors.</li>
  <li>Engage journalism organisations (First Draft, Bellingcat) to apply detection
      tools where they matter most.</li>
</ul>

<h3>Resources</h3>
<ul>
  <li>FaceForensics++ — standard detection benchmark and dataset</li>
  <li>NIST DFAD — Deepfake Analysis and Detection evaluation</li>
  <li>DFDC (Deepfake Detection Challenge) — Facebook / AWS / Microsoft / PAI</li>
  <li>MIT Media Lab — Camera Culture group deepfake research</li>
  <li>Witness Media Lab — media verification training for journalists</li>
</ul>

<p><b>DeepSentinel is provided solely for education, research, and defensive
security. Misuse violates this project's licence and applicable law.</b></p>
""",
},

}  # end SECTIONS
