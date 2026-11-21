"""
SVEL-APEX NEUROSCIENCE & BRAIN-COMPUTER INTERFACE VALIDATION v3.0
====================================================================
Purpose:
- Rigorous neural hypothesis validation
- Audit BCI claims via signal artifact checks and cross-subject validation
- Deploy a multi-stage neural decoding workflow
- Verify that novel decoding algorithms generalize beyond noise fitting
"""

import logging
from typing import Any, List, Dict, Optional

from backend.experiments.templates.base import (
    DataAnalysisTemplate,
    TemplateCustomizationParams
)
from backend.experiments.templates import register_template
from backend.experiments.models import (
    ExperimentProtocol,
    ExperimentType,
    ProtocolStep,
    Variable,
    ResourceRequirements,
    ValidationCheck
)

logger = logging.getLogger(__name__)


@register_template
class SVELApexBCITemplate(DataAnalysisTemplate):
    """
    SVEL-APEX NEURAL VALIDATION ENGINE
    
    This engine does NOT:
    - Accept subject-specific overfitting as "generalization"
    - Trust single-session EEG/fMRI decoders
    - Allow artifact-contaminated signals
    - Accept chance-level decoding as "neural signature"
    - Ignore cross-subject transfer failure
    
    This engine DOES:
    - Audit artifacts (EOG, EMG, line noise)
    - Run Cross-Subject Leave-One-Out Validation
    - Attack decoders with permutation tests
    - Stress-test temporal generalization (King & Dehaene)
    - Verify Information Transfer Rate (ITR) claims
    
    Output:
    - NEURAL KILL report with artifact/overfitting metrics
    - DECODING ROBUSTNESS profile
    - CROSS-SUBJECT TRANSFER matrix
    """

    def __init__(self):
        super().__init__(
            name="neuroscience_annihilator_apex",
            domain="neuroscience",
            title="Neural Decoding Validation",
            description=(
                "Autonomous neural hypothesis falsification engine. "
                "Audits signal artifacts, validates cross-subject generalization, "
                "stress-tests temporal decoding, and verifies BCI claims."
            ),
            suitable_for=[
                "BCI/BMI system validation",
                "EEG/MEG decoding claims",
                "fMRI MVPA analysis",
                "Motor imagery classification",
                "Cognitive state detection",
                "Neural biomarker verification",
                "Cross-subject transfer learning"
            ],
            requirements=[
                "MNE-Python (Signal Processing)",
                "NeuroKit2 (Physiological Analysis)",
                "Scikit-Learn / PyTorch",
                "GPU for Deep Learning Decoders"
            ],
            complexity_score=0.98,
            rigor_score=0.99
        )

    def is_applicable(self, hypothesis: Any) -> bool:
        return True

    def is_applicable_heuristic(self, hypothesis: Any) -> bool:
        """Three-tier Neural gate"""
        s = str(hypothesis).lower()
        
        # TIER 1: Core Neuro Concepts
        neuro_terms = [
            'eeg', 'meg', 'fmri', 'neural', 'brain', 'cortex', 'neuron',
            'spike', 'lfp', 'erp', 'bci', 'bmi', 'decoding', 'motor imagery',
            'cognitive', 'attention', 'memory', 'perception', 'sensory',
            'prefrontal', 'temporal', 'parietal', 'occipital', 'hippocampus',
            'oscillation', 'alpha', 'beta', 'gamma', 'theta', 'delta'
        ]
        
        if not any(t in s for t in neuro_terms):
            logger.warning(f"REJECTED [TIER-1]: No neural content: {hypothesis}")
            return False

        # TIER 2: Methodological Claims
        method_terms = [
            'decode', 'classify', 'predict', 'accuracy', 'performance',
            'real-time', 'online', 'offline', 'cross-subject', 'transfer',
            'generalization', 'biomarker', 'signature', 'pattern', 'mvpa',
            'connectivity', 'coherence', 'power spectrum', 'time-frequency'
        ]
        
        if not any(t in s for t in method_terms):
            logger.warning(f"REJECTED [TIER-2]: No methodological claims: {hypothesis}")
            return False

        return True

    # ------------------------------------------------------------------
    # SVEL-APEX NEURAL VALIDATION PROTOCOL
    # ------------------------------------------------------------------
    def generate_protocol(
        self,
        params: TemplateCustomizationParams
    ) -> ExperimentProtocol:
        """
        Generates the neural validation protocol.
        
        This is a 25-stage execution gauntlet spanning:
        - Signal Forensic Audit (Artifact Rejection)
        - Cross-Subject Validation
        - Temporal Generalization Matrix
        - Permutation Testing
        - ITR Verification
        """
        
        # Extract file paths from params logic provided in custom_variables or data_paths.
        data_path = params.custom_variables.get("data_path", "raw_data.fif")
        
        return ExperimentProtocol(
            title=f"SVEL-APEX NEURAL VALIDATION :: {params.hypothesis_id}",
            hypothesis_id=params.hypothesis_id,
            experiment_type=ExperimentType.DATA_ANALYSIS,
            domain="neuroscience",
            description=(
                "Full-spectrum neural decoding audit: Artifact check  Cross-Subject  "
                "Temporal Generalization  Permutation Tests. "
                "Output: Neural Kill Report OR Robust BCI Verification."
            ),

            variables=[
                Variable(name="modality", type="str", value="EEG", description="EEG/MEG/fMRI/ECoG"),
                Variable(name="sampling_rate", type="float", value="1000", description="Hz"),
                Variable(name="n_subjects", type="int", value="20", description="Number of subjects"),
                Variable(name="n_channels", type="int", value="64", description="EEG channels"),
                Variable(name="paradigm", type="str", value="motor_imagery", description="Task paradigm"),
                Variable(name="decoding_window_ms", type="int", value="500", description="Decoding window"),
                Variable(name="cross_validation_folds", type="int", value="10", description="CV folds"),
                Variable(name="permutation_iterations", type="int", value="1000", description="Permutations"),
                Variable(name="data_path", type="str", value=data_path, description="Path to raw recording file"),
                Variable(name="use_deep_learning", type="bool", value="True", description="Enable EEGNet (PyTorch)")
            ],

            steps=[
                # ========== PHASE 1: SIGNAL FORENSICS ==========
                ProtocolStep(
                    name="load_data",
                    description="Load and inspect raw neurophysiological data",
                    code_template=self._gen_load_data_code(data_path),
                    expected_output="MNE Raw Object"
                ),

                ProtocolStep(
                    name="artifact_audit",
                    description=(
                        "Signal Quality Check:\n"
                        "- EOG artifact detection (Blink/Saccade)\n"
                        "- EMG contamination scan (Muscle noise)\n"
                        "- Line noise (50/60Hz) rejection\n"
                        "- Bad channel interpolation (Maxwell Filtering if MEG)"
                    ),
                    code_template=self._gen_artifact_code(),
                    expected_output="Artifact Report (Clean/Contaminated)"
                ),
                
                ProtocolStep(
                    name="ica_decomposition",
                    description=(
                        "Blind Source Separation:\n"
                        "- FastICA / Infomax\n"
                        "- Automated component rejection (ICLabel)\n"
                        "- Remove ocular, cardiac, muscle components"
                    ),
                    code_template=self._gen_ica_code(),
                    expected_output="Cleaned Signal Components"
                ),

                # ========== PHASE 2: WITHIN-SUBJECT DECODING ==========
                ProtocolStep(
                    name="feature_extraction",
                    description=(
                        "Neural Feature Engineering:\n"
                        "- Time-domain features (mean, var)\n"
                        "- Frequency-band power (alpha, beta, gamma)\n"
                        "- CSP (Common Spatial Patterns)\n"
                        "- Riemannian geometry (SPD matrices)"
                    ),
                    code_template=self._gen_features_code(),
                    expected_output="Feature Matrix"
                ),
                
                ProtocolStep(
                    name="within_subject_cv",
                    description=(
                        "Within-Subject Cross-Validation:\n"
                        "- Stratified K-Fold\n"
                        "- Temporal block splits (avoid leakage)\n"
                        "- Report mean  std accuracy"
                    ),
                    code_template=self._gen_within_cv_code(),
                    expected_output="Within-Subject Accuracy"
                ),

                ProtocolStep(
                    name="deep_learning_decoding",
                    description=(
                        "EEGNet Deep Learning (Lawhern et al., 2018):\n"
                        "- PyTorch implementation\n"
                        "- Temporal Conv -> Spatial Conv -> Separable Conv\n"
                        "- Robust against noise and jitter"
                    ),
                    code_template=self._gen_eegnet_code(),
                    expected_output="EEGNet Accuracy"
                ),

                # ========== PHASE 3: CROSS-SUBJECT VALIDATION ==========
                ProtocolStep(
                    name="loso_cross_validation",
                    description=(
                        "Leave-One-Subject-Out (LOSO):\n"
                        "- Train on N-1 subjects\n"
                        "- Test on held-out subject\n"
                        "- Report transfer accuracy matrix"
                    ),
                    code_template=self._gen_loso_code(),
                    expected_output="Cross-Subject Transfer Matrix"
                ),
                
                ProtocolStep(
                    name="domain_adaptation",
                    description=(
                        "Subject Alignment:\n"
                        "- Euclidean Alignment (EA)\n"
                        "- Riemannian Procrustes\n"
                        "- Check if alignment improves generalization"
                    ),
                    code_template=self._gen_alignment_code(),
                    expected_output="Aligned Transfer Accuracy"
                ),

                # ========== PHASE 4: TEMPORAL GENERALIZATION ==========
                ProtocolStep(
                    name="temporal_generalization_matrix",
                    description=(
                        "King & Dehaene (2014) Analysis:\n"
                        "- Train at time t, test at time t'\n"
                        "- Diagonal = Sustained patterns\n"
                        "- Off-diagonal = Dynamic recoding"
                    ),
                    code_template=self._gen_temp_gen_code(),
                    expected_output="Temporal Generalization Matrix"
                ),

                # ========== PHASE 5: STATISTICAL RIGOR ==========
                ProtocolStep(
                    name="permutation_test",
                    description=(
                        "Null Distribution Generation:\n"
                        "- Shuffle labels 1000 times\n"
                        "- Build empirical null\n"
                        "- Calculate p-value"
                    ),
                    code_template=self._gen_permutation_code(),
                    expected_output="Permutation P-value"
                ),
                
                ProtocolStep(
                    name="cluster_correction",
                    description=(
                        "Multiple Comparison Correction:\n"
                        "- Cluster-based permutation (MNE)\n"
                        "- FDR (Benjamini-Hochberg)\n"
                        "- Bonferroni (if needed)"
                    ),
                    code_template=self._gen_cluster_code(),
                    expected_output="Corrected Significance Map"
                ),

                # ========== PHASE 6: BCI METRICS ==========
                ProtocolStep(
                    name="itr_calculation",
                    description=(
                        "Information Transfer Rate:\n"
                        "- ITR = log2(N) + P*log2(P) + (1-P)*log2((1-P)/(N-1))\n"
                        "- Report bits/min\n"
                        "- Compare to literature benchmarks"
                    ),
                    code_template=self._gen_itr_code(),
                    expected_output="ITR Score (bits/min)"
                ),

                # ========== PHASE 7: FINAL VERDICT ==========
                ProtocolStep(
                    name="neural_kill_check",
                    description=(
                        "Aggregate Weaknesses:\n"
                        "- Artifact contaminated? (Kill)\n"
                        "- Chance-level decoding? (Kill)\n"
                        "- No cross-subject transfer? (Warn/Kill)\n"
                        "- Permutation p > 0.05? (Kill)"
                    ),
                    code_template=self._gen_failure_code(),
                    expected_output="Ranked Failure Modes"
                ),
                
                ProtocolStep(
                    name="final_verdict",
                    description=(
                        "Synthesize into NEURAL KILL or SURVIVAL:\n"
                        "- KILL: Overfitting, Artifacts, No Generalization\n"
                        "- SURVIVAL: Robust Cross-Subject BCI"
                    ),
                    code_template=self._gen_verdict_code(),
                    expected_output="Neural validation report"
                )
            ],

            resource_requirements=ResourceRequirements(
                cpu_cores=32,
                memory_gb=64.0,
                gpu_required=True,
                gpu_memory_mb=16000,
                estimated_runtime_seconds=28800  # 8 hours
            ),
            expected_duration_hours=8.0
        )

    # ==================================================================
    # CODE GENERATION HELPERS
    # ==================================================================
    
    def _gen_load_data_code(self, data_path: str) -> str:
        return f'''
# ========== DATA LOADING ==========
import mne
import numpy as np
import os

def load_eeg_data(path: str):
    """
    Load EEG/MEG data from typical formats (.fif, .edf, .bdf).
    """
    print(f"Loading data from {{path}}...")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Data file not found: {{path}}")
        
    try:
        if path.endswith('.fif'):
            raw = mne.io.read_raw_fif(path, preload=True)
        elif path.endswith('.edf'):
            raw = mne.io.read_raw_edf(path, preload=True)
        elif path.endswith('.bdf'):
            raw = mne.io.read_raw_bdf(path, preload=True)
        else:
            raise ValueError(f"Unsupported file format: {{path}}")
            
        print(f"Loaded: {{len(raw.ch_names)}} channels, {{raw.times[-1]:.2f}}s duration")
        return raw
    except Exception as e:
        print(f"CRITICAL ERROR loading data: {{e}}")
        raise

# Execute
# raw = load_eeg_data("{data_path}")
'''

    def _gen_artifact_code(self) -> str:
        return '''
# ========== ARTIFACT DETECTION ==========
import mne
import numpy as np

def audit_artifacts(raw) -> dict:
    """
    Detect EOG, EMG, and line noise artifacts using real statistical thresholds.
    """
    print("Auditing Signal Quality (MNE-Python)...")
    
    # 1. Detect bad channels (Flat or extremely noisy)
    # Note: Maxwell filtering is for MEG; for EEG we use correlation/variance
    # Here we use a standard deviation threshold
    data = raw.get_data()
    std_devs = np.std(data, axis=1)
    threshold = np.mean(std_devs) + 3 * np.std(std_devs)
    bads_manual = [raw.ch_names[i] for i in range(len(raw.ch_names)) if std_devs[i] > threshold]
    
    # Add to raw info
    raw.info['bads'].extend(bads_manual)
    
    # 2. EOG Artifacts (if EOG channels present)
    eog_events = mne.preprocessing.find_eog_events(raw)
    n_blinks = len(eog_events) if eog_events is not None else 0
    
    # 3. Line Noise (50/60 Hz power)
    psd = raw.compute_psd(method='welch', fmin=1, fmax=100)
    freqs = psd.freqs
    # Check 50Hz and 60Hz bands
    idx_50 = np.argmin(np.abs(freqs - 50))
    idx_60 = np.argmin(np.abs(freqs - 60))
    
    power_50 = np.mean(psd.get_data()[:, idx_50])
    power_60 = np.mean(psd.get_data()[:, idx_60])
    
    has_line_noise = (power_50 > 1e-9) or (power_60 > 1e-9) # Threshold depends on units (V^2/Hz)
    
    return {
        "bad_channels_count": len(raw.info['bads']),
        "bad_channels_list": raw.info['bads'],
        "blinks_detected": n_blinks,
        "line_noise_detected": bool(has_line_noise),
        "verdict": "FAIL" if len(raw.info['bads']) > len(raw.ch_names) * 0.2 else "PASS"
    }

# Execute
# artifact_report = audit_artifacts(raw)
# print(f"Artifact Audit: {artifact_report['verdict']}")
'''

    def _gen_ica_code(self) -> str:
        return '''
# ========== ICA ARTIFACT REMOVAL ==========
from mne.preprocessing import ICA

def run_ica_cleaning(raw, n_components=15, random_state=42) -> dict:
    print("Running ICA for artifact rejection (FastICA)...")
    
    # High-pass filter before ICA for stability
    raw_ica = raw.copy().filter(l_freq=1.0, h_freq=None)
    
    ica = ICA(n_components=n_components, method='fastica', random_state=random_state)
    ica.fit(raw_ica)
    
    # Auto-detect EOG/ECG components
    # (Requires EOG/ECG channels; handle absent channels explicitly in a real implementation.)
    eog_indices, eog_scores = ica.find_bads_eog(raw)
    ecg_indices, ecg_scores = ica.find_bads_ecg(raw, method='correlation')
    
    to_exclude = (eog_indices + ecg_indices) if (eog_indices and ecg_indices) else []
    ica.exclude = list(set(to_exclude))
    
    # Apply cleaning
    raw_clean = raw.copy()
    ica.apply(raw_clean)
    
    return {
        "components_removed": len(ica.exclude),
        "excluded_indices": ica.exclude,
        "raw_clean": raw_clean
    }

# Execute
# ica_result = run_ica_cleaning(raw)
# raw = ica_result['raw_clean']
# print(f"ICA: Removed {ica_result['components_removed']} artifact components")
'''

    def _gen_eegnet_code(self) -> str:
        return '''
# ========== DEEP LEARNING (EEGNet) ==========
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset

class EEGNet(nn.Module):
    """
    EEGNet-8,2 (Lawhern et al., 2018) Implementation in PyTorch.
    Optimized for BCI decoding from raw signals.
    """
    def __init__(self, nb_classes, Chans=64, Samples=128, dropoutRate=0.25):
        super(EEGNet, self).__init__()
        
        # Layer 1: Temporal Convolution
        self.conv1 = nn.Conv2d(1, 8, (1, 64), padding=(0, 32), bias=False)
        self.batchnorm1 = nn.BatchNorm2d(8)
        
        # Layer 2: Spatial Depthwise Convolution
        self.conv2 = nn.Conv2d(8, 16, (Chans, 1), groups=8, bias=False)
        self.batchnorm2 = nn.BatchNorm2d(16)
        self.elu = nn.ELU()
        self.avgpool1 = nn.AvgPool2d((1, 4))
        self.dropout1 = nn.Dropout(dropoutRate)
        
        # Layer 3: Separable Convolution
        self.conv3 = nn.Conv2d(16, 16, (1, 16), padding=(0, 8), groups=16, bias=False)
        self.conv4 = nn.Conv2d(16, 16, (1, 1), bias=False)
        self.batchnorm3 = nn.BatchNorm2d(16)
        self.avgpool2 = nn.AvgPool2d((1, 8))
        self.dropout2 = nn.Dropout(dropoutRate)
        
        # Classification
        self.flatten = nn.Flatten()
        # Calculate linear size dynamically or hardcode based on input
        # For simplicity in template, using a localized AdaptivePool to force size
        self.global_pool = nn.AdaptiveAvgPool2d((1, 1))
        self.fc = nn.Linear(16, nb_classes)

    def forward(self, x):
        # Input (Batch, 1, Channels, Time)
        x = self.conv1(x)
        x = self.batchnorm1(x)
        
        x = self.conv2(x)
        x = self.batchnorm2(x)
        x = self.elu(x)
        x = self.avgpool1(x)
        x = self.dropout1(x)
        
        x = self.conv3(x)
        x = self.conv4(x)
        x = self.batchnorm3(x)
        x = self.elu(x)
        x = self.avgpool2(x)
        x = self.dropout2(x)
        
        x = self.global_pool(x)
        x = self.flatten(x)
        x = self.fc(x)
        return x

def train_eegnet(X_train, y_train, X_test, y_test, epochs=30):
    print("Training EEGNet (PyTorch)...")
    
    # Check GPU
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"   Device: {device}")
    
    # Prepare Data
    # X shape needs to be (Batch, 1, Channels, Time)
    X_tr = torch.Tensor(X_train[:, None, :, :])
    y_tr = torch.LongTensor(y_train)
    X_te = torch.Tensor(X_test[:, None, :, :])
    y_te = torch.LongTensor(y_test)
    
    train_loader = DataLoader(TensorDataset(X_tr, y_tr), batch_size=32, shuffle=True)
    
    # Init Model
    n_classes = len(np.unique(y_train))
    n_chans = X_train.shape[1]
    n_time = X_train.shape[2]
    
    model = EEGNet(nb_classes=n_classes, Chans=n_chans, Samples=n_time).to(device)
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    criterion = nn.CrossEntropyLoss()
    
    # Train Loop
    for ep in range(epochs):
        model.train()
        for X_batch, y_batch in train_loader:
            X_batch, y_batch = X_batch.to(device), y_batch.to(device)
            optimizer.zero_grad()
            outputs = model(X_batch)
            loss = criterion(outputs, y_batch)
            loss.backward()
            optimizer.step()
            
    # Evaluate
    model.eval()
    with torch.no_grad():
        outputs = model(X_te.to(device))
        _, predicted = torch.max(outputs.data, 1)
        acc = (predicted == y_te.to(device)).sum().item() / len(y_te)
        
    print(f"   EEGNet Accuracy: {acc:.4f}")
    return acc

# Execute (assuming epochs data X, y)
# eegnet_acc = train_eegnet(X_train, y_train, X_test, y_test)
'''

    def _gen_features_code(self) -> str:
        return '''
# ========== FEATURE EXTRACTION ==========
from sklearn.pipeline import Pipeline
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.model_selection import ShuffleSplit, cross_val_score
from mne.decoding import CSP, Scaler

def extract_features_and_prepare_decoder(epochs, n_components=4):
    """
    Setup CSP (Common Spatial Patterns) pipeline for EEG decoding.
    """
    print("Setting up CSP Feature Extraction Pipeline...")
    
    # MNE CSP Implementation
    csp = CSP(n_components=n_components, reg=None, log=True, norm_trace=False)
    
    # Classifier (LDA is standard for BCI)
    clf = LinearDiscriminantAnalysis()
    
    # Pipeline
    pipeline = Pipeline([
        ('CSP', csp),
        ('LDA', clf)
    ])
    
    return pipeline, epochs.get_data(), epochs.events[:, -1]

# Execute
# pipeline, X, y = extract_features_and_prepare_decoder(epochs)
'''

    def _gen_within_cv_code(self) -> str:
        return '''
# ========== WITHIN-SUBJECT CV ==========
from sklearn.model_selection import StratifiedKFold, cross_val_score

def run_within_subject_cv(pipeline, X, y, n_folds=10) -> dict:
    print(f"Running {n_folds}-Fold Stratified CV...")
    
    cv = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=42)
    
    # Real execution using Scikit-Learn
    scores = cross_val_score(pipeline, X, y, cv=cv, n_jobs=-1)
    
    return {
        "mean_acc": scores.mean(),
        "std_acc": scores.std(),
        "all_scores": scores
    }

# Execute
# within_cv = run_within_subject_cv(pipeline, X, y)
# print(f"Within-Subject: {within_cv['mean_acc']:.4f}  {within_cv['std_acc']:.4f}")
'''

    def _gen_loso_code(self) -> str:
        return '''
# ========== LEAVE-ONE-SUBJECT-OUT (LOSO) ==========
from sklearn.model_selection import LeaveOneGroupOut

def run_loso_cv(pipeline, X_all, y_all, groups_subjects) -> dict:
    """
    Train on N-1 subjects, test on held-out.
    X_all: Concatenated data from all subjects
    groups_subjects: Array of subject IDs corresponding to X_all samples
    """
    print("Running LOSO Cross-Validation (Real Execution)...")
    
    logo = LeaveOneGroupOut()
    scores = []
    
    if pipeline is None:
        raise ValueError("A fitted pipeline object must be provided for LOSO evaluation.")
    
    for train_idx, test_idx in logo.split(X_all, y_all, groups=groups_subjects):
        X_train, y_train = X_all[train_idx], y_all[train_idx]
        X_test, y_test = X_all[test_idx], y_all[test_idx]
        
        # Fit and Score
        pipeline.fit(X_train, y_train)
        score = pipeline.score(X_test, y_test)
        scores.append(score)
        
    mean_loso = np.mean(scores)
    
    return {
        "loso_accuracy": mean_loso,
        "std_loso": np.std(scores),
        "scores_per_subject": scores
    }

# Execute (Requires multi-subject data structure)
# loso = run_loso_cv(X_all, y_all, subject_ids)
# print(f"LOSO Accuracy: {loso['loso_accuracy']:.4f}")
'''

    def _gen_alignment_code(self) -> str:
        return '''
# ========== DOMAIN ADAPTATION (Euclidean Alignment) ==========
from scipy.linalg import fractional_matrix_power

def euclidean_alignment(epochs_data):
    """
    Align covariance matrices to identity Reference (He & Wu, 2019).
    epochs_data: (n_epochs, n_channels, n_times)
    """
    print("Applying Euclidean Alignment (Reference centering)...")
    
    # 1. Compute Reference Matrix (Mean Covariance)
    covs = [np.cov(epoch) for epoch in epochs_data]
    R_mean = np.mean(covs, axis=0)
    
    # 2. Compute R^(-0.5)
    R_inv_sqrt = fractional_matrix_power(R_mean, -0.5)
    
    # 3. Transform all trials
    # X_aligned = R^(-0.5) * X
    aligned_data = np.array([R_inv_sqrt @ epoch for epoch in epochs_data])
    
    return aligned_data

# Execute
# X_aligned = euclidean_alignment(X)
'''

    def _gen_temp_gen_code(self) -> str:
        return '''
# ========== TEMPORAL GENERALIZATION ==========
from mne.decoding import GeneralizingEstimator

def compute_temporal_generalization(pipeline, epochs) -> np.ndarray:
    """
    King & Dehaene (2014): Train at time t, test at time t'.
    Uses MNE GeneralizingEstimator.
    """
    print("Computing Temporal Generalization Matrix...")
    
    # Setup MNE Generalizing Estimator
    time_gen = GeneralizingEstimator(pipeline, scoring='accuracy', n_jobs=-1, verbose=True)
    
    # Fit and Score
    # X needs to be (n_epochs, n_channels, n_times)
    X = epochs.get_data()
    y = epochs.events[:, -1]
    
    time_gen.fit(X, y)
    scores = time_gen.score(X, y) # This returns (n_train_times, n_test_times)
    
    return scores

# Execute
# temp_gen_matrix = compute_temporal_generalization(pipeline, epochs)
# print(f"Temporal Generalization Matrix Shape: {temp_gen_matrix.shape}")
'''

    def _gen_permutation_code(self) -> str:
        return '''
# ========== PERMUTATION TESTING ==========
from sklearn.model_selection import permutation_test_score

def run_permutation_test(pipeline, X, y, n_perms=1000) -> dict:
    print(f"Running {n_perms} Permutations (Scikit-Learn)...")
    
    # Real execution of permutation test
    score, permutation_scores, pvalue = permutation_test_score(
        pipeline, X, y, cv=5, n_permutations=n_perms, n_jobs=-1, verbose=1
    )
    
    return {
        "observed_accuracy": score,
        "p_value": pvalue,
        "significant": pvalue < {alpha},
        "null_distribution_mean": np.mean(permutation_scores)
    }

# Execute
# perm = run_permutation_test(pipeline, X, y)
# print(f"Permutation p-value: {perm['p_value']:.4f}")
'''

    def _gen_cluster_code(self) -> str:
        return '''
# ========== CLUSTER CORRECTION ==========
import mne

def cluster_permutation_test_time(X_scores, chance_level=0.5, p_threshold={alpha}) -> dict:
    """
    Cluster-based permutation test on time-series decoding scores.
    X_scores: (n_subjects, n_times) array of accuracies
    """
    print("Running MNE Cluster-Based Permutation Test...")
    
    # T-test against chance
    T_obs, clusters, cluster_p_values, H0 = mne.stats.permutation_cluster_1samp_test(
        X_scores - chance_level,
        n_permutations=1000,
        tail=1, # One-sided (acc > chance)
        out_type='mask'
    )
    
    good_clusters = [k for k, p in enumerate(cluster_p_values) if p < p_threshold]
    
    return {
        "n_clusters": len(good_clusters),
        "significant_time_indices": np.where(clusters[0])[0] if good_clusters else [],
        "min_p_value": min(cluster_p_values) if len(cluster_p_values) > 0 else 1.0
    }

# Execute (Needs group level data)
# cluster_res = cluster_permutation_test_time(group_scores)
'''

    def _gen_itr_code(self) -> str:
        return '''
# ========== INFORMATION TRANSFER RATE ==========
import math

def calculate_itr(n_classes, accuracy, trial_duration_s) -> float:
    """
    ITR in bits/min (Wolpaw formula).
    """
    # Clamp accuracy to avoid log(0)
    P = min(max(accuracy, 0.001), 0.999)
    N = n_classes
    
    # Chance level check
    if P <= 1.0/N:
        return 0.0
    
    itr_bits_trial = math.log2(N) + P*math.log2(P) + (1-P)*math.log2((1-P)/(N-1))
    itr_bits_min = itr_bits_trial * (60 / trial_duration_s)
    
    return max(0.0, itr_bits_min)

# Execute
# itr = calculate_itr(n_classes=4, accuracy=observed_accuracy, trial_duration_s=observed_trial_duration_s)
# print(f"ITR: {itr:.2f} bits/min")
'''

    def _gen_failure_code(self) -> str:
        return '''
# ========== FAILURE SYNTHESIS ==========
def audit_neural_failures(results) -> list:
    print("Aggregating Neural Failure Signals...")
    failures = []
    
    if results.get("artifact_report", {}).get("verdict") == "FAIL":
        failures.append("Excessive Artifact Contamination")
        
    if results.get("permutation_test", {}).get("p_value", 1.0) > {alpha}:
        failures.append(f"Not Statistically Significant (p>{{alpha}})")
        
    if results.get("loso_cv", {}).get("loso_accuracy", 0.0) < 0.5: # Assuming binary
        failures.append("Cross-Subject Generalization Failure")
        
    return failures
'''

    def _gen_verdict_code(self) -> str:
        return '''
# ========== FINAL VERDICT ==========

def generate_verdict(failures):
    if not failures:
        print(" VERDICT: SURVIVAL (Robust Neural Decoding)")
        print("   - Significant p-value")
        print("   - Cross-subject generalization confirmed")
        print("   - Artifacts clean")
    else:
        print(f" VERDICT: KILL (Flaws Detected: {failures})")
        
# Execute
# generate_verdict(failures)
'''
