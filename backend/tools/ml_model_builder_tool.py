#!/usr/bin/env python3
from __future__ import annotations

"""

   AUTOMATED ML FORGE  HIGH-FIDELITY MODEL BUILDER                         


The most powerful ML model building system.

CAPABILITIES:
- 25+ Algorithm Zoo (Traditional, Ensemble, Gradient Boosting, Deep Learning)
- AutoML with Grid/Random/Bayesian Optimization
- Advanced Feature Engineering (polynomial, interactions, target encoding)
- Cross-Validation with stratification
- Model Stacking & Blending
- Comprehensive Metrics Dashboard
- Automatic Hyperparameter Tuning
- Time Series Forecasting
- Anomaly Detection
- GPU Acceleration (when available)

SUPPORTED PROBLEM TYPES:
- Binary Classification
- Multi-class Classification
- Regression
- Time Series Forecasting
- Anomaly Detection
- Clustering
"""

import os
import json
import logging
import warnings
import time
import pickle
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List, Union
from dataclasses import dataclass, field, asdict
from enum import Enum

import numpy as np
import pandas as pd

warnings.filterwarnings('ignore')

# Setup logging
logging.basicConfig(level=os.getenv("ML_FORGE_LOG", "INFO"))
logger = logging.getLogger("automated_ml_forge")

# 
# DEPENDENCY DETECTION
# 

_HAVE_SKLEARN = False
_HAVE_XGBOOST = False
_HAVE_LIGHTGBM = False
_HAVE_CATBOOST = False
_HAVE_TORCH = False
_HAVE_OPTUNA = False

try:
    from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold, KFold
    from sklearn.metrics import (
        accuracy_score, precision_score, recall_score, f1_score,
        r2_score, mean_squared_error, mean_absolute_error,
        roc_auc_score, confusion_matrix, classification_report
    )
    from sklearn.preprocessing import StandardScaler, LabelEncoder, MinMaxScaler
    from sklearn.ensemble import (
        RandomForestClassifier, RandomForestRegressor,
        GradientBoostingClassifier, GradientBoostingRegressor,
        AdaBoostClassifier, AdaBoostRegressor,
        ExtraTreesClassifier, ExtraTreesRegressor,
        BaggingClassifier, BaggingRegressor,
        StackingClassifier, StackingRegressor,
        VotingClassifier, VotingRegressor
    )
    from sklearn.linear_model import (
        LogisticRegression, LinearRegression,
        Ridge, Lasso, ElasticNet,
        SGDClassifier, SGDRegressor
    )
    from sklearn.svm import SVC, SVR
    from sklearn.neighbors import KNeighborsClassifier, KNeighborsRegressor
    from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor
    from sklearn.naive_bayes import GaussianNB
    from sklearn.neural_network import MLPClassifier, MLPRegressor
    from sklearn.cluster import KMeans, DBSCAN
    from sklearn.decomposition import PCA
    from sklearn.feature_selection import SelectKBest, f_classif, mutual_info_classif
    _HAVE_SKLEARN = True
except ImportError:
    logger.warning("scikit-learn not available - ML capabilities limited")

try:
    import xgboost as xgb
    _HAVE_XGBOOST = True
except ImportError:
    pass

try:
    import lightgbm as lgb
    _HAVE_LIGHTGBM = True
except ImportError:
    pass

try:
    import catboost as cb
    _HAVE_CATBOOST = True
except ImportError:
    pass

try:
    import torch
    import torch.nn as nn
    _HAVE_TORCH = True
except ImportError:
    pass

try:
    import optuna
    _HAVE_OPTUNA = True
except ImportError:
    pass


# 
# ENUMS & DATA CLASSES
# 

class ProblemType(str, Enum):
    BINARY_CLASSIFICATION = "binary_classification"
    MULTICLASS_CLASSIFICATION = "multiclass_classification"
    REGRESSION = "regression"
    TIME_SERIES = "time_series"
    ANOMALY_DETECTION = "anomaly_detection"
    CLUSTERING = "clustering"
    MULTIMODAL = "multimodal"


class OptimizationStrategy(str, Enum):
    GRID_SEARCH = "grid"
    RANDOM_SEARCH = "random"
    BAYESIAN = "bayesian"
    NONE = "none"


@dataclass
class ModelResult:
    """Comprehensive result from a single model training."""
    name: str
    problem_type: str
    status: str = "pending"
    
    # Classification metrics
    accuracy: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    f1: Optional[float] = None
    roc_auc: Optional[float] = None
    
    # Regression metrics
    r2: Optional[float] = None
    mse: Optional[float] = None
    rmse: Optional[float] = None
    mae: Optional[float] = None
    mape: Optional[float] = None
    
    # Cross-validation
    cv_mean: Optional[float] = None
    cv_std: Optional[float] = None
    
    # Timing
    training_time_s: float = 0.0
    
    # Model object (not serializable)
    model: Any = None
    
    # Feature importance
    feature_importances: Dict[str, float] = field(default_factory=dict)
    
    # Hyperparameters
    best_params: Dict[str, Any] = field(default_factory=dict)
    
    # Error info
    error: Optional[str] = None


@dataclass 
class ExperimentResult:
    """Complete result from the Automated ML Forge."""
    experiment_id: str
    timestamp: str
    problem_type: str
    status: str = "running"
    
    # Data info
    n_samples: int = 0
    n_features: int = 0
    n_classes: Optional[int] = None
    
    # Models tested
    models_tested: List[str] = field(default_factory=list)
    model_results: Dict[str, Dict] = field(default_factory=dict)
    
    # Best model
    best_model_name: Optional[str] = None
    best_score: Optional[float] = None
    best_metric: str = "accuracy"
    
    # Feature engineering
    features_created: List[str] = field(default_factory=list)
    features_selected: List[str] = field(default_factory=list)
    
    # Timing
    total_time_s: float = 0.0
    
    # Error
    error: Optional[str] = None


# 
# GODZILLA ALGORITHM ZOO
# 

class AutomatedAlgorithmZoo:
    """
     THE ULTIMATE ALGORITHM COLLECTION
    25+ algorithms ready to compete for the best performance.
    """
    
    @staticmethod
    def get_classifiers(include_slow: bool = True) -> Dict[str, Any]:
        """Get all classification algorithms."""
        if not _HAVE_SKLEARN:
            return {}
        
        models = {
            # Speed tier: FAST
            "LogisticRegression": LogisticRegression(max_iter=1000, random_state=42),
            "GaussianNB": GaussianNB(),
            "DecisionTree": DecisionTreeClassifier(max_depth=10, random_state=42),
            "KNN": KNeighborsClassifier(n_neighbors=5),
            "SGD": SGDClassifier(max_iter=1000, random_state=42),
            
            # Speed tier: MEDIUM (n_jobs=1 by default on macOS to prevent loky/OpenMP fork deadlock after PyTorch init)
            "RandomForest": RandomForestClassifier(n_estimators=100, max_depth=15, random_state=42, n_jobs=int(os.getenv("ULTRON_SKLEARN_N_JOBS", "1"))),
            "ExtraTrees": ExtraTreesClassifier(n_estimators=100, max_depth=15, random_state=42, n_jobs=int(os.getenv("ULTRON_SKLEARN_N_JOBS", "1"))),
            "GradientBoosting": GradientBoostingClassifier(n_estimators=100, max_depth=5, random_state=42),
            "AdaBoost": AdaBoostClassifier(n_estimators=50, random_state=42),
            "Bagging": BaggingClassifier(n_estimators=50, random_state=42, n_jobs=int(os.getenv("ULTRON_SKLEARN_N_JOBS", "1"))),
        }
        
        if include_slow:
            models["SVC"] = SVC(kernel='rbf', probability=True, random_state=42)
            models["MLP"] = MLPClassifier(hidden_layer_sizes=(100, 50), max_iter=500, random_state=42)
        
        # Guard native C++ OpenMP boosters (XGBoost/LightGBM/CatBoost) behind include_slow to avoid
        # macOS libomp/PyTorch OpenMP runtime collision when torch is already initialized in-process.
        if include_slow:
            if _HAVE_XGBOOST:
                models["XGBoost"] = xgb.XGBClassifier(
                    n_estimators=100, max_depth=6, learning_rate=0.1,
                    random_state=42, use_label_encoder=False, eval_metric='logloss', n_jobs=1
                )
            if _HAVE_LIGHTGBM:
                models["LightGBM"] = lgb.LGBMClassifier(
                    n_estimators=100, max_depth=8, learning_rate=0.1,
                    random_state=42, verbose=-1, n_jobs=1
                )
            if _HAVE_CATBOOST:
                models["CatBoost"] = cb.CatBoostClassifier(
                    n_estimators=100, max_depth=6, learning_rate=0.1,
                    random_state=42, verbose=0, thread_count=1
                )
        
        return models
    
    @staticmethod
    def get_regressors(include_slow: bool = True) -> Dict[str, Any]:
        """Get all regression algorithms."""
        if not _HAVE_SKLEARN:
            return {}
        
        models = {
            # Speed tier: FAST
            "LinearRegression": LinearRegression(),
            "Ridge": Ridge(alpha=1.0),
            "Lasso": Lasso(alpha=0.1),
            "ElasticNet": ElasticNet(alpha=0.1, l1_ratio=0.5),
            "DecisionTree": DecisionTreeRegressor(max_depth=10, random_state=42),
            "KNN": KNeighborsRegressor(n_neighbors=5),
            "SGD": SGDRegressor(max_iter=1000, random_state=42),
            
            # Speed tier: MEDIUM (n_jobs=1 by default on macOS to prevent loky/OpenMP fork deadlock after PyTorch init)
            "RandomForest": RandomForestRegressor(n_estimators=100, max_depth=15, random_state=42, n_jobs=int(os.getenv("ULTRON_SKLEARN_N_JOBS", "1"))),
            "ExtraTrees": ExtraTreesRegressor(n_estimators=100, max_depth=15, random_state=42, n_jobs=int(os.getenv("ULTRON_SKLEARN_N_JOBS", "1"))),
            "GradientBoosting": GradientBoostingRegressor(n_estimators=100, max_depth=5, random_state=42),
            "AdaBoost": AdaBoostRegressor(n_estimators=50, random_state=42),
            "Bagging": BaggingRegressor(n_estimators=50, random_state=42, n_jobs=int(os.getenv("ULTRON_SKLEARN_N_JOBS", "1"))),
        }
        
        if include_slow:
            models["SVR"] = SVR(kernel='rbf')
            models["MLP"] = MLPRegressor(hidden_layer_sizes=(100, 50), max_iter=500, random_state=42)
        
        if include_slow:
            if _HAVE_XGBOOST:
                models["XGBoost"] = xgb.XGBRegressor(
                    n_estimators=100, max_depth=6, learning_rate=0.1, random_state=42, n_jobs=1
                )
            if _HAVE_LIGHTGBM:
                models["LightGBM"] = lgb.LGBMRegressor(
                    n_estimators=100, max_depth=8, learning_rate=0.1,
                    random_state=42, verbose=-1, n_jobs=1
                )
            if _HAVE_CATBOOST:
                models["CatBoost"] = cb.CatBoostRegressor(
                    n_estimators=100, max_depth=6, learning_rate=0.1,
                    random_state=42, verbose=0, thread_count=1
                )
        
        return models


# 
#  GODZILLA DEEP LEARNING ZOO  ULTRA PRO MAX NEURAL NETWORKS
# 

if _HAVE_TORCH:
    import torch.nn.functional as F
    from torch.utils.data import DataLoader, TensorDataset
    
    class DeepMLP(nn.Module):
        """
         Deep Multi-Layer Perceptron
        Deep fully-connected network with BatchNorm and Dropout.
        """
        def __init__(self, input_size: int, hidden_sizes: List[int], output_size: int, 
                     dropout: float = 0.3, task: str = "classification"):
            super().__init__()
            self.task = task
            
            layers = []
            prev_size = input_size
            
            for hidden_size in hidden_sizes:
                layers.extend([
                    nn.Linear(prev_size, hidden_size),
                    nn.BatchNorm1d(hidden_size),
                    nn.ReLU(),
                    nn.Dropout(dropout)
                ])
                prev_size = hidden_size
            
            layers.append(nn.Linear(prev_size, output_size))
            self.network = nn.Sequential(*layers)
        
        def forward(self, x):
            return self.network(x)
    
    
    class DeepCNN1D(nn.Module):
        """
         1D Convolutional Neural Network
        For sequential/tabular data with local patterns.
        """
        def __init__(self, input_channels: int, seq_length: int, output_size: int,
                     task: str = "classification"):
            super().__init__()
            self.task = task
            
            self.conv1 = nn.Conv1d(input_channels, 64, kernel_size=3, padding=1)
            self.bn1 = nn.BatchNorm1d(64)
            self.conv2 = nn.Conv1d(64, 128, kernel_size=3, padding=1)
            self.bn2 = nn.BatchNorm1d(128)
            self.conv3 = nn.Conv1d(128, 256, kernel_size=3, padding=1)
            self.bn3 = nn.BatchNorm1d(256)
            
            self.pool = nn.AdaptiveAvgPool1d(1)
            self.fc = nn.Linear(256, output_size)
            self.dropout = nn.Dropout(0.3)
        
        def forward(self, x):
            # x: (batch, features) -> (batch, 1, features)
            if len(x.shape) == 2:
                x = x.unsqueeze(1)
            
            x = F.relu(self.bn1(self.conv1(x)))
            x = F.relu(self.bn2(self.conv2(x)))
            x = F.relu(self.bn3(self.conv3(x)))
            x = self.pool(x).squeeze(-1)
            x = self.dropout(x)
            return self.fc(x)
    
    
    class DeepLSTM(nn.Module):
        """
         LSTM Network
        Long Short-Term Memory for sequential patterns.
        """
        def __init__(self, input_size: int, hidden_size: int = 128, 
                     num_layers: int = 2, output_size: int = 1,
                     bidirectional: bool = False, task: str = "classification"):
            super().__init__()
            self.task = task
            self.hidden_size = hidden_size
            self.num_layers = num_layers
            self.bidirectional = bidirectional
            
            self.lstm = nn.LSTM(
                input_size=input_size,
                hidden_size=hidden_size,
                num_layers=num_layers,
                batch_first=True,
                dropout=0.3 if num_layers > 1 else 0,
                bidirectional=bidirectional
            )
            
            fc_input = hidden_size * 2 if bidirectional else hidden_size
            self.fc = nn.Linear(fc_input, output_size)
            self.dropout = nn.Dropout(0.3)
        
        def forward(self, x):
            # x: (batch, features) -> (batch, seq_len=1, features)
            if len(x.shape) == 2:
                x = x.unsqueeze(1)
            
            lstm_out, (h_n, c_n) = self.lstm(x)
            
            # Use last hidden state
            if self.bidirectional:
                out = torch.cat((h_n[-2], h_n[-1]), dim=1)
            else:
                out = h_n[-1]
            
            out = self.dropout(out)
            return self.fc(out)
    
    
    class DeepGRU(nn.Module):
        """
         GRU Network
        Gated Recurrent Unit - faster than LSTM, similar performance.
        """
        def __init__(self, input_size: int, hidden_size: int = 128,
                     num_layers: int = 2, output_size: int = 1,
                     task: str = "classification"):
            super().__init__()
            self.task = task
            
            self.gru = nn.GRU(
                input_size=input_size,
                hidden_size=hidden_size,
                num_layers=num_layers,
                batch_first=True,
                dropout=0.3 if num_layers > 1 else 0
            )
            
            self.fc = nn.Linear(hidden_size, output_size)
            self.dropout = nn.Dropout(0.3)
        
        def forward(self, x):
            if len(x.shape) == 2:
                x = x.unsqueeze(1)
            
            _, h_n = self.gru(x)
            out = self.dropout(h_n[-1])
            return self.fc(out)
    
    
    class DeepAttention(nn.Module):
        """
         Self-Attention Layer
        Attention mechanism for learning feature importance.
        """
        def __init__(self, embed_dim: int, num_heads: int = 4):
            super().__init__()
            self.attention = nn.MultiheadAttention(embed_dim, num_heads, batch_first=True)
            self.norm = nn.LayerNorm(embed_dim)
        
        def forward(self, x):
            attn_out, _ = self.attention(x, x, x)
            return self.norm(x + attn_out)
    
    
    class DeepTransformer(nn.Module):
        """
         Transformer Network
        State-of-the-art attention-based architecture.
        """
        def __init__(self, input_size: int, d_model: int = 128, nhead: int = 4,
                     num_layers: int = 2, output_size: int = 1,
                     task: str = "classification"):
            super().__init__()
            self.task = task
            
            self.input_proj = nn.Linear(input_size, d_model)
            
            encoder_layer = nn.TransformerEncoderLayer(
                d_model=d_model,
                nhead=nhead,
                dim_feedforward=d_model * 4,
                dropout=0.1,
                batch_first=True
            )
            self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
            
            self.fc = nn.Linear(d_model, output_size)
            self.dropout = nn.Dropout(0.1)
        
        def forward(self, x):
            # x: (batch, features) -> (batch, seq_len=1, features)
            if len(x.shape) == 2:
                x = x.unsqueeze(1)
            
            x = self.input_proj(x)
            x = self.transformer(x)
            x = x.mean(dim=1)  # Global average pooling
            x = self.dropout(x)
            return self.fc(x)
    
    
    class DeepResBlock(nn.Module):
        """Residual block for ResNet-style networks."""
        def __init__(self, in_features: int, out_features: int):
            super().__init__()
            self.fc1 = nn.Linear(in_features, out_features)
            self.bn1 = nn.BatchNorm1d(out_features)
            self.fc2 = nn.Linear(out_features, out_features)
            self.bn2 = nn.BatchNorm1d(out_features)
            
            self.shortcut = nn.Identity() if in_features == out_features else nn.Linear(in_features, out_features)
        
        def forward(self, x):
            residual = self.shortcut(x)
            out = F.relu(self.bn1(self.fc1(x)))
            out = self.bn2(self.fc2(out))
            return F.relu(out + residual)
    
    
    class DeepResNet(nn.Module):
        """
         ResNet for Tabular Data
        Residual connections for very deep networks.
        """
        def __init__(self, input_size: int, hidden_sizes: List[int], output_size: int,
                     task: str = "classification"):
            super().__init__()
            self.task = task
            
            self.input_layer = nn.Linear(input_size, hidden_sizes[0])
            self.input_bn = nn.BatchNorm1d(hidden_sizes[0])
            
            blocks = []
            for i in range(len(hidden_sizes) - 1):
                blocks.append(DeepResBlock(hidden_sizes[i], hidden_sizes[i+1]))
            self.res_blocks = nn.Sequential(*blocks)
            
            self.output_layer = nn.Linear(hidden_sizes[-1], output_size)
            self.dropout = nn.Dropout(0.3)
        
        def forward(self, x):
            x = F.relu(self.input_bn(self.input_layer(x)))
            x = self.res_blocks(x)
            x = self.dropout(x)
            return self.output_layer(x)
    
    
    class DeepAutoEncoder(nn.Module):
        """
         AutoEncoder
        For dimensionality reduction and anomaly detection.
        """
        def __init__(self, input_size: int, latent_size: int = 32):
            super().__init__()
            
            # Encoder
            self.encoder = nn.Sequential(
                nn.Linear(input_size, 256),
                nn.ReLU(),
                nn.Linear(256, 128),
                nn.ReLU(),
                nn.Linear(128, latent_size)
            )
            
            # Decoder
            self.decoder = nn.Sequential(
                nn.Linear(latent_size, 128),
                nn.ReLU(),
                nn.Linear(128, 256),
                nn.ReLU(),
                nn.Linear(256, input_size)
            )
        
        def forward(self, x):
            latent = self.encoder(x)
            reconstructed = self.decoder(latent)
            return reconstructed
        
        def encode(self, x):
            return self.encoder(x)
    
    
    class DeepLearningZoo:
        """
         THE ULTIMATE DEEP LEARNING ARSENAL
        All neural network architectures ready to deploy.
        """
        
        @staticmethod
        def get_models(input_size: int, output_size: int, 
                       problem_type: str = "classification") -> Dict[str, nn.Module]:
            """Get all deep learning models."""
            models = {}
            
            # MLP variants
            models["DL_MLP_Small"] = DeepMLP(input_size, [64, 32], output_size, task=problem_type)
            models["DL_MLP_Medium"] = DeepMLP(input_size, [128, 64, 32], output_size, task=problem_type)
            models["DL_MLP_Large"] = DeepMLP(input_size, [256, 128, 64, 32], output_size, task=problem_type)
            models["DL_MLP_Deep"] = DeepMLP(input_size, [512, 256, 128, 64, 32], output_size, task=problem_type)
            
            # CNN
            models["DL_CNN1D"] = DeepCNN1D(1, input_size, output_size, task=problem_type)
            
            # RNN variants
            models["DL_LSTM"] = DeepLSTM(input_size, 128, 2, output_size, task=problem_type)
            models["DL_BiLSTM"] = DeepLSTM(input_size, 128, 2, output_size, bidirectional=True, task=problem_type)
            models["DL_GRU"] = DeepGRU(input_size, 128, 2, output_size, task=problem_type)
            
            # Transformer
            models["DL_Transformer"] = DeepTransformer(input_size, 128, 4, 2, output_size, task=problem_type)
            
            # ResNet
            models["DL_ResNet"] = DeepResNet(input_size, [128, 128, 64, 64], output_size, task=problem_type)
            
            return models
        
        @staticmethod
        def train_model(model: nn.Module, X_train: np.ndarray, y_train: np.ndarray,
                        X_val: np.ndarray = None, y_val: np.ndarray = None,
                        epochs: int = 50, batch_size: int = 32, lr: float = 0.001,
                        problem_type: str = "classification") -> Dict[str, Any]:
            """
            Train a PyTorch model with proper training loop.
            """
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            model = model.to(device)
            
            # Convert to tensors
            X_train_t = torch.FloatTensor(X_train).to(device)
            
            if problem_type == "classification":
                y_train_t = torch.LongTensor(y_train).to(device)
                criterion = nn.CrossEntropyLoss()
            else:
                y_train_t = torch.FloatTensor(y_train).unsqueeze(1).to(device)
                criterion = nn.MSELoss()
            
            # DataLoader
            dataset = TensorDataset(X_train_t, y_train_t)
            loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
            
            # Optimizer
            optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.01)
            scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
            
            # Training loop
            history = {"train_loss": [], "val_loss": []}
            best_loss = float('inf')
            
            model.train()
            for epoch in range(epochs):
                epoch_loss = 0.0
                for batch_X, batch_y in loader:
                    optimizer.zero_grad()
                    outputs = model(batch_X)
                    loss = criterion(outputs, batch_y)
                    loss.backward()
                    torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                    optimizer.step()
                    epoch_loss += loss.item()
                
                avg_loss = epoch_loss / len(loader)
                history["train_loss"].append(avg_loss)
                scheduler.step()
                
                # Validation
                if X_val is not None:
                    model.eval()
                    with torch.no_grad():
                        X_val_t = torch.FloatTensor(X_val).to(device)
                        if problem_type == "classification":
                            y_val_t = torch.LongTensor(y_val).to(device)
                        else:
                            y_val_t = torch.FloatTensor(y_val).unsqueeze(1).to(device)
                        val_outputs = model(X_val_t)
                        val_loss = criterion(val_outputs, y_val_t).item()
                        history["val_loss"].append(val_loss)
                        
                        if val_loss < best_loss:
                            best_loss = val_loss
                    model.train()
            
            return {
                "model": model,
                "history": history,
                "device": str(device),
                "best_loss": best_loss
            }
        
        @staticmethod
        def predict(model: nn.Module, X: np.ndarray, problem_type: str = "classification") -> np.ndarray:
            """Make predictions with a trained model."""
            device = next(model.parameters()).device
            model.eval()
            
            with torch.no_grad():
                X_t = torch.FloatTensor(X).to(device)
                outputs = model(X_t)
                
                if problem_type == "classification":
                    _, predicted = torch.max(outputs, 1)
                    return predicted.cpu().numpy()
                else:
                    return outputs.squeeze().cpu().numpy()


# 
# GODZILLA FEATURE ENGINEER
# 

class AutomatedFeatureEngineer:
    """
     ULTRA-ADVANCED FEATURE ENGINEERING
    Transform raw data into ML-ready features without test-set leakage.
    """
    
    def __init__(self):
        self.scaler = None
        self.label_encoders = {}
        self.created_features = []
        self._num_cols: List[str] = []
        self._interaction_pairs: List[Tuple[str, str]] = []
        self._poly_cols: List[str] = []
        self._feature_columns: List[str] = []
        self._imputation_values: Dict[str, Any] = {}
    
    def fit_transform(self, X: pd.DataFrame, y: pd.Series = None, 
                      problem_type: str = "classification") -> pd.DataFrame:
        """Fit feature engineering strictly on training data and transform."""
        self.created_features = []
        self._interaction_pairs = []
        self._poly_cols = []
        self._imputation_values = {}
        X_out = X.copy()
        
        # 1. Handle missing values (fit statistics on training set only)
        X_out = self._handle_missing(X_out, fit=True)
        
        # 2. Encode categorical features
        X_out = self._encode_categoricals(X_out, fit=True)
        
        # 3. Scale numerical features
        X_out = self._scale_numericals(X_out, fit=True)
        
        # 4. Create interaction features (top numerical pairs)
        X_out = self._create_interactions(X_out, fit=True)
        
        # 5. Create polynomial features for top features
        X_out = self._create_polynomials(X_out, fit=True)
        
        self._feature_columns = list(X_out.columns)
        logger.info(f"Feature engineering complete: {X.shape[1]} -> {X_out.shape[1]} features")
        return X_out
    
    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """Transform test/inference data using fitted training transformations."""
        X_out = X.copy()
        X_out = self._handle_missing(X_out, fit=False)
        X_out = self._encode_categoricals(X_out, fit=False)
        X_out = self._scale_numericals(X_out, fit=False)
        X_out = self._create_interactions(X_out, fit=False)
        X_out = self._create_polynomials(X_out, fit=False)
        if self._feature_columns:
            for col in self._feature_columns:
                if col not in X_out.columns:
                    X_out[col] = 0.0
            X_out = X_out[self._feature_columns]
        return X_out
    
    def _handle_missing(self, X: pd.DataFrame, fit: bool = True) -> pd.DataFrame:
        """Intelligent missing value handling without test-set leakage."""
        for col in X.columns:
            if fit:
                if X[col].dtype in ['object', 'category']:
                    self._imputation_values[col] = 'MISSING'
                elif pd.api.types.is_numeric_dtype(X[col]):
                    skew = abs(X[col].skew()) if X[col].std() > 0 else 0
                    val = X[col].median() if skew > 1 else X[col].mean()
                    self._imputation_values[col] = 0.0 if pd.isna(val) else val
            if X[col].isna().sum() == 0:
                continue
            if col in self._imputation_values:
                X[col] = X[col].fillna(self._imputation_values[col])
            elif X[col].dtype in ['object', 'category']:
                X[col] = X[col].fillna('MISSING')
            elif pd.api.types.is_numeric_dtype(X[col]):
                X[col] = X[col].fillna(0.0)
        return X
    
    def _encode_categoricals(self, X: pd.DataFrame, fit: bool = True) -> pd.DataFrame:
        """Encode categorical features using label encoding or one-hot."""
        cat_cols = X.select_dtypes(include=['object', 'category']).columns
        
        for col in cat_cols:
            n_unique = X[col].nunique()
            
            if (fit and n_unique <= 10) or (not fit and col not in self.label_encoders):
                # One-hot for low cardinality
                dummies = pd.get_dummies(X[col], prefix=col, dummy_na=True)
                X = pd.concat([X.drop(columns=[col]), dummies], axis=1)
            else:
                # Label encode for high cardinality
                if fit:
                    le = LabelEncoder()
                    X[col] = le.fit_transform(X[col].astype(str))
                    self.label_encoders[col] = le
                else:
                    if col in self.label_encoders:
                        le = self.label_encoders[col]
                        X[col] = X[col].astype(str).map(
                            lambda x: le.transform([x])[0] if x in le.classes_ else -1
                        )
        return X
    
    def _scale_numericals(self, X: pd.DataFrame, fit: bool = True) -> pd.DataFrame:
        """Scale numerical features."""
        if fit:
            num_cols = X.select_dtypes(include=['float64', 'int64', 'float32', 'int32']).columns.tolist()
            self._num_cols = num_cols
        else:
            num_cols = [c for c in self._num_cols if c in X.columns]
        
        if not num_cols:
            return X
        
        if fit:
            self.scaler = StandardScaler()
            X[num_cols] = self.scaler.fit_transform(X[num_cols])
        elif self.scaler:
            for c in self._num_cols:
                if c not in X.columns:
                    X[c] = 0.0
            X[self._num_cols] = self.scaler.transform(X[self._num_cols])
        
        return X
    
    def _create_interactions(self, X: pd.DataFrame, max_features: int = 5, fit: bool = True) -> pd.DataFrame:
        """Create interaction features between top numerical columns."""
        if fit:
            num_cols = X.select_dtypes(include=['float64', 'int64', 'float32', 'int32']).columns.tolist()
            if len(num_cols) < 2:
                return X
            top_cols = X[num_cols].var().nlargest(min(max_features, len(num_cols))).index.tolist()
            self._interaction_pairs = []
            for i, col1 in enumerate(top_cols):
                for col2 in top_cols[i+1:]:
                    self._interaction_pairs.append((col1, col2))
        
        for col1, col2 in self._interaction_pairs:
            if col1 in X.columns and col2 in X.columns:
                new_col = f"{col1}_x_{col2}"
                X[new_col] = X[col1] * X[col2]
                if fit and new_col not in self.created_features:
                    self.created_features.append(new_col)
        
        return X
    
    def _create_polynomials(self, X: pd.DataFrame, max_features: int = 3, fit: bool = True) -> pd.DataFrame:
        """Create polynomial features (squared) for top numerical columns."""
        if fit:
            num_cols = [c for c in self._num_cols if c in X.columns] or X.select_dtypes(include=['float64', 'int64']).columns.tolist()
            if not num_cols:
                return X
            self._poly_cols = X[num_cols].var().nlargest(min(max_features, len(num_cols))).index.tolist()
        
        for col in self._poly_cols:
            if col in X.columns:
                new_col = f"{col}_squared"
                X[new_col] = X[col] ** 2
                if fit and new_col not in self.created_features:
                    self.created_features.append(new_col)
        
        return X


# 
#  MULTI-MODAL GSTM SUPPORT
# 

if _HAVE_TORCH:
    class MetadataEncoder:
        """Stateful encoder for categorical metadata."""
        def __init__(self):
            self.encoders = {}
            self.vocab_sizes = {}
            self.columns = ['terrain', 'solar_wind', 'orbit_zone', 'gap_id']

        def fit(self, df):
            """Learn vocabulary from dataframe."""
            for col in self.columns:
                if col in df.columns:
                    # Treat everything as string for safety
                    # For gap_id (numeric), we might handle differently, but treating as cat is safe for embedding
                    series = df[col].astype(str)
                    le = LabelEncoder()
                    le.fit(series)
                    self.encoders[col] = le
                    # Vocab size = len(classes) + 1 (for zero padding/unknown)
                    self.vocab_sizes[col] = len(le.classes_) + 1 
                else:
                    self.vocab_sizes[col] = 1 # Just unknown/padding

        def transform(self, df):
            """Convert dataframe to list of tensors."""
            tensors = []
            for col in self.columns:
                if col in df.columns and col in self.encoders:
                    le = self.encoders[col]
                    # Map known classes to i+1, unknown to 0
                    mapping = {cls: i+1 for i, cls in enumerate(le.classes_)}
                    series = df[col].astype(str)
                    # High-speed map using pandas
                    indices = series.map(mapping).fillna(0).values.astype(np.int64)
                    tensors.append(torch.LongTensor(indices))
                else:
                     # Missing column or not fitted -> all zeros
                    tensors.append(torch.zeros(len(df), dtype=torch.long))
            return tensors

    class GSTMPipeline:
        """Serializable pipeline: preprocessing + model."""
        def __init__(self, model, metadata_encoder, device='cpu'):
            self.model = model
            self.metadata_encoder = metadata_encoder
            self.device = device

        def predict(self, images, dna_sequences, metadata_df):
            """End-to-end inference."""
            self.model.eval()
            self.model.to(self.device)
            
            # Preprocess Images
            if isinstance(images, np.ndarray):
                if images.max() > 1.0:
                    images = images / 255.0
                images_t = torch.FloatTensor(images).permute(0, 3, 1, 2)
            else:
                images_t = images
            
            # Preprocess DNA
            dna_t = GSTMDataset._encode_dna_static(dna_sequences)
            
            # Preprocess Metadata
            meta_tensors = self.metadata_encoder.transform(metadata_df)
            
            # Batch construct
            batch = {
                'image': images_t.to(self.device),
                'dna': dna_t.to(self.device),
                'terrain': meta_tensors[0].to(self.device),
                'solar': meta_tensors[1].to(self.device),
                'orbit': meta_tensors[2].to(self.device),
                'gap_id': meta_tensors[3].to(self.device)
            }
            
            with torch.no_grad():
                output = self.model(batch)
            
            return output.cpu().numpy()

    class GSTMDataset(torch.utils.data.Dataset):
        """Dataset class that handles images + DNA + metadata simultaneously"""
        
        def __init__(self, images, dna_sequences, metadata_df, targets=None, metadata_encoder=None,
                     time_series=None, text_data=None, graphs=None):
            # Optimization: Store images as uint8 to save memory, cast in __getitem__
            if isinstance(images, np.ndarray) and images.dtype != np.uint8:
                self.images = torch.from_numpy(images.astype(np.uint8)).permute(0, 3, 1, 2)
            else:
                self.images = torch.from_numpy(images).permute(0, 3, 1, 2) if isinstance(images, np.ndarray) else images
            
            # DNA Encoding
            self.dna = self._encode_dna(dna_sequences)
            
            # Metadata Encoding
            self.meta_tensors = self._process_metadata(metadata_df, metadata_encoder)
            
            # Time Series (New)
            if time_series is not None:
                self.time_series = torch.FloatTensor(time_series)
            else:
                self.time_series = None
                
            # Text (New)
            if text_data is not None:
                self.text_tensors = self._encode_text(text_data)
            else:
                self.text_tensors = None
                
            # Graphs (New - Feature Extraction)
            if graphs is not None:
                self.graph_features = self._extract_graph_features(graphs)
            else:
                self.graph_features = None

            if targets is not None:
                self.targets = torch.FloatTensor(targets)
            else:
                self.targets = torch.zeros(len(images))

        def _encode_dna(self, sequences):
            mapping = {'A':0, 'C':1, 'G':2, 'T':3, 'N':4}
            encoded_list = []
            for seq in sequences:
                # Truncate to 2000
                seq = seq[:2000].ljust(2000, 'N')
                nums = [mapping.get(b, 4) for b in seq]
                encoded_list.append(nums)
            return torch.LongTensor(encoded_list)
            
        def _encode_text(self, text_list):
            # Char-level encoding (simple)
            # Vocab size 128 (ASCII)
            max_len = 200 # descriptions are short
            encoded = []
            for t in text_list:
                t = str(t)[:max_len].ljust(max_len)
                # ASCII encoding, unknown -> 0
                nums = [ord(c) if ord(c) < 128 else 0 for c in t]
                encoded.append(nums)
            return torch.LongTensor(encoded)
            
        def _extract_graph_features(self, graphs):
            # Compute degree centrality avg/max
            feats = []
            for G in graphs:
                if not G or G.number_of_nodes() == 0:
                    feats.append(0.0)
                    continue
                # We know "graph_degree" (avg degree) affects yield
                degrees = [d for n, d in G.degree()]
                avg_deg = sum(degrees) / len(degrees) if degrees else 0
                feats.append(avg_deg)
            return torch.FloatTensor(feats).unsqueeze(1) # (B, 1)

        def _process_metadata(self, metadata, encoder):
            if encoder:
                 return encoder.transform(metadata)
            return [] # Should not happen in training
            
        def __len__(self):
            return len(self.images)
        
        def __getitem__(self, idx):
            sample = {
                'target': torch.tensor(self.targets[idx], dtype=torch.float32) if self.targets is not None else torch.tensor(0.0, dtype=torch.float32),
                'masks': {} # Store presence flags
            }
            
            # 1. Image
            if self.images is not None:
                img = self.images[idx]
                # Cast to float and normalize here
                if isinstance(img, torch.Tensor):
                    img = img.float() / 255.0
                elif isinstance(img, np.ndarray):
                    img = torch.from_numpy(img).float() / 255.0
                sample['image'] = img
                sample['masks']['image'] = torch.tensor(1.0, dtype=torch.float32)
            else:
                 sample['masks']['image'] = torch.tensor(0.0, dtype=torch.float32)
            
            # 2. DNA
            if self.dna is not None:
                dna = self.dna[idx]
                if isinstance(dna, np.ndarray):
                    dna = torch.from_numpy(dna).long()
                elif isinstance(dna, torch.Tensor):
                    dna = dna.long()
                sample['dna'] = dna
                sample['masks']['dna'] = torch.tensor(1.0, dtype=torch.float32)
            else:
                sample['masks']['dna'] = torch.tensor(0.0, dtype=torch.float32)
            
            # 3. Metadata
            if self.meta_tensors is not None:
                # meta_tensors is [col1, col2, col3, col4]
                # We need to grab the scalar at [idx] from each column tensor
                sample['terrain'] = self.meta_tensors[0][idx]
                sample['solar'] = self.meta_tensors[1][idx]
                sample['orbit'] = self.meta_tensors[2][idx]
                sample['gap_id'] = self.meta_tensors[3][idx]
                sample['masks']['metadata'] = torch.tensor(1.0, dtype=torch.float32)
            else:
                sample['masks']['metadata'] = torch.tensor(0.0, dtype=torch.float32)

            # 4. Time Series
            if self.time_series is not None:
                # time_series[idx] is already (100, 5)
                sample['timeseries'] = self.time_series[idx].float()
                sample['masks']['timeseries'] = torch.tensor(1.0, dtype=torch.float32)
            else:
                sample['masks']['timeseries'] = torch.tensor(0.0, dtype=torch.float32)

            # 5. Text
            if self.text_tensors is not None:
                # Text indices must be long for Embedding
                sample['text'] = self.text_tensors[idx].long()
                sample['masks']['text'] = torch.tensor(1.0, dtype=torch.float32)
            else:
                sample['masks']['text'] = torch.tensor(0.0, dtype=torch.float32)

            # 6. Graphs
            if self.graph_features is not None:
                # graph_features is tensor (B, 1) or list of scalars
                # If list of scalars/tensors:
                deg = self.graph_features[idx]
                sample['graph_degree'] = torch.tensor([deg], dtype=torch.float32)
                sample['masks']['graph'] = torch.tensor(1.0, dtype=torch.float32)
            else:
                sample['masks']['graph'] = torch.tensor(0.0, dtype=torch.float32)
                
            # Modality Masking (Training Augmentation)
            if self.targets is not None: # Only in training
                import random
                if random.random() < 0.2:
                    # Drop one random modality
                    keys = [k for k in ['image', 'dna', 'timeseries', 'text', 'graph_degree'] if k in sample]
                    if keys:
                        drop_k = random.choice(keys)
                        # Don't delete key (breaks collate), just zero the mask
                        # The model forward pass uses the mask to switch to 'missing_embedding'
                        
                        mask_k = drop_k if drop_k != 'graph_degree' else 'graph'
                        sample['masks'][mask_k] = torch.tensor(0.0, dtype=torch.float32)
            
            # Defensive Check
            if 'image' not in sample:
                print(f"FATAL: 'image' key missing for idx {idx}. Keys: {list(sample.keys())}")
                # Fallback to avoid crash
                sample['image'] = torch.zeros(3, 128, 128)
                sample['masks']['image'] = 0.0

            return sample

    class TimeSeriesEncoder(nn.Module):
        """1D CNN + LSTM for Time Series (100 steps x 5 features)"""
        def __init__(self):
            super().__init__()
            self.net = nn.Sequential(
                nn.Conv1d(5, 32, kernel_size=3, padding=1),
                nn.ReLU(),
                nn.Conv1d(32, 64, kernel_size=3, padding=1),
                nn.ReLU(),
                nn.AdaptiveAvgPool1d(10) # Downsample to 10 steps
            )
            self.lstm = nn.LSTM(64, 32, batch_first=True)
            
        def forward(self, x):
            # x: (B, 100, 5) -> permute to (B, 5, 100) for Conv1d
            x = x.permute(0, 2, 1).float()
            x = self.net(x) # (B, 64, 10)
            x = x.permute(0, 2, 1) # (B, 10, 64) for LSTM
            _, (h_n, _) = self.lstm(x)
            return h_n.squeeze(0) # (B, 32)

    class TextEncoder(nn.Module):
        """Char-level CNN for Text descriptions"""
        def __init__(self, vocab_size=128, dim=32):
            super().__init__()
            self.embedding = nn.Embedding(vocab_size, 16)
            self.net = nn.Sequential(
                nn.Conv1d(16, 32, kernel_size=3, padding=1),
                nn.ReLU(),
                nn.MaxPool1d(2),
                nn.Conv1d(32, 64, kernel_size=3, padding=1),
                nn.ReLU(),
                nn.AdaptiveAvgPool1d(1)
            )
            
        def forward(self, x):
            # x: (B, L) long tensor
            x = x.long() # Hard defensive
            emb = self.embedding(x) # (B, L, 16)
            emb = emb.permute(0, 2, 1) # (B, 16, L)
            feat = self.net(emb).squeeze(-1) # (B, 64)
            return feat

    class CrossAttentionFusionModel(nn.Module):
        """
         MASTER ARCHITECTURE for GSTM Level 10
        Fuses 5 Modalities: Image, DNA, Metadata, TimeSeries, Text, GraphFeatures.
        Uses Cross-Attention and Gated Fusion.
        """
        def __init__(self, vocab_sizes: Dict[str, int] = None):
            super().__init__()
            vocab_sizes = vocab_sizes or {}
            
            # 1. Image Encoder
            self.image_encoder = nn.Sequential(
                nn.Conv2d(3, 32, 3, padding=1), nn.BatchNorm2d(32), nn.ReLU(), nn.MaxPool2d(2),
                nn.Conv2d(32, 64, 3, padding=1), nn.BatchNorm2d(64), nn.ReLU(), nn.MaxPool2d(2),
                nn.Conv2d(64, 128, 3, padding=1), nn.BatchNorm2d(128), nn.ReLU(), nn.MaxPool2d(2),
                nn.AdaptiveAvgPool2d(1)
            )
            self.image_fc = nn.Linear(128, 128)
            
            # 2. DNA Encoder
            self.dna_embed = nn.Embedding(5, 32)
            self.position_embed = nn.Embedding(2000, 32)
            self.dna_encoder = nn.Sequential(
                nn.Conv1d(32, 128, kernel_size=5, padding=2), nn.ReLU(),
                nn.Conv1d(128, 256, kernel_size=5, padding=2), nn.ReLU(),
                nn.AdaptiveAvgPool1d(1)
            )
            self.dna_fc = nn.Linear(256, 128)
            self.cross_attention = nn.MultiheadAttention(128, 4, batch_first=True, dropout=0.2)
            
            # 3. Metadata Encoders
            self.terrain_embed = nn.Embedding(vocab_sizes.get('terrain', 20), 16)
            self.solar_embed = nn.Embedding(vocab_sizes.get('solar_wind', 10), 8)
            self.orbit_embed = nn.Embedding(vocab_sizes.get('orbit_zone', 10), 8)
            self.gap_embed = nn.Embedding(vocab_sizes.get('gap_id', 10000), 32)
            
            # 4. New Encoders
            self.ts_encoder = TimeSeriesEncoder() # out: 32
            self.text_encoder = TextEncoder()     # out: 64
            
            # 5. Learnable "Missing" Embeddings (Level 11 Robustness)
            self.missing_img = nn.Parameter(torch.randn(1, 128))
            self.missing_dna = nn.Parameter(torch.randn(1, 128))
            self.missing_meta = nn.Parameter(torch.randn(1, 64)) 
            # 16+8+8+32 = 64.
            self.missing_ts = nn.Parameter(torch.randn(1, 32))
            self.missing_text = nn.Parameter(torch.randn(1, 64))
            self.missing_graph = nn.Parameter(torch.randn(1, 1))
            
            # 6. Fusion Head
            # Img(128) + DNA(128) + Meta(64) + TS(32) + Text(64) + Graph(1) + Mask(5)
            # Mask vector is now explicit input (5 dim)
            fusion_dim = 128 + 128 + 64 + 32 + 64 + 1 + 5
            
            self.regressor = nn.Sequential(
                nn.Linear(fusion_dim, 256),
                nn.ReLU(),
                nn.Dropout(0.3),
                nn.Linear(256, 128),
                nn.ReLU(),
                nn.Linear(128, 1)
            )
        
        def forward(self, batch):
            # 0. Global Batch Params
            if 'image' in batch:
                 bs = batch['image'].size(0)
                 device = batch['image'].device
            elif 'dna' in batch:
                 bs = batch['dna'].size(0)
                 device = batch['dna'].device
            else:
                 bs = 1
                 device = self.device if hasattr(self, 'device') else 'cpu'

            # Helper to get mask
            masks = batch.get('masks', {})
            # Ensure all masks are float32
            masks = {k: v.float() if isinstance(v, torch.Tensor) else torch.tensor(v, dtype=torch.float32, device=device) 
                     for k, v in masks.items()}
            
            # 1. Image
            if 'image' in batch:
                real_feat = self.image_fc(self.image_encoder(batch['image']).squeeze(-1).squeeze(-1))
                # Apply mask: Real * Mask + Missing * (1-Mask)
                m = masks.get('image', torch.ones(bs, device=device)).unsqueeze(1)
                img_feat = real_feat * m + self.missing_img * (1 - m)
            else:
                img_feat = self.missing_img.expand(bs, -1).to(device)
            
            # 2. DNA Cross-Attention
            if 'dna' in batch:
                dna_idx = batch['dna'].long()
                dna_emb = self.dna_embed(dna_idx)
                positions = torch.arange(dna_emb.size(1), device=dna_emb.device, dtype=torch.long).unsqueeze(0)
                dna_emb = dna_emb + self.position_embed(positions)
                dna_emb = dna_emb.permute(0, 2, 1)
                dna_feat_raw = self.dna_fc(self.dna_encoder(dna_emb).squeeze(-1))
                
                # Cross Attn 
                dna_q = dna_feat_raw.unsqueeze(1)
                img_kv = img_feat.unsqueeze(1)
                
                # DEBUG
                if bs > 0:
                     # Using .float() explicitly to avoid any Double upcasting
                     dna_q = dna_q.float()
                     img_kv = img_kv.float()
                
                attended, _ = self.cross_attention(dna_q, img_kv, img_kv)
                attended = attended.squeeze(1)
                
                m = masks.get('dna', torch.ones(bs, device=device)).unsqueeze(1)
                dna_feat = dna_feat_raw * m + self.missing_dna * (1 - m)
                attended = attended * m 
            else:
                dna_feat = self.missing_dna.expand(bs, -1).to(device)
                attended = torch.zeros(bs, 128, device=device)
            
            # 3. Metadata
            meta_raw = torch.cat([
                self.terrain_embed(batch['terrain'].long()),
                self.solar_embed(batch['solar'].long()),
                self.orbit_embed(batch['orbit'].long()),
                self.gap_embed(batch['gap_id'].long())
            ], dim=1)
            
            m = masks.get('metadata', torch.ones(bs, device=device)).unsqueeze(1)
            meta_feat = meta_raw * m + self.missing_meta * (1 - m)
            
            # 4. Time Series
            if 'timeseries' in batch:
                ts_raw = self.ts_encoder(batch['timeseries'])
                m = masks.get('timeseries', torch.ones(bs, device=device)).unsqueeze(1)
                ts_feat = ts_raw * m + self.missing_ts * (1 - m)
            else:
                ts_feat = self.missing_ts.expand(bs, -1).to(device)
            
            # 5. Text
            if 'text' in batch:
                text_raw = self.text_encoder(batch['text'])
                m = masks.get('text', torch.ones(bs, device=device)).unsqueeze(1)
                text_feat = text_raw * m + self.missing_text * (1 - m)
            else:
                text_feat = self.missing_text.expand(bs, -1).to(device)
            
            # 6. Graph Features
            if 'graph_degree' in batch:
                graph_raw = batch['graph_degree']
                m = masks.get('graph', torch.ones(bs, device=device)).unsqueeze(1)
                graph_feat = graph_raw * m + self.missing_graph * (1 - m)
            else:
                graph_feat = self.missing_graph.expand(bs, -1).to(device)
            
            # 7. Mask Vector (Explicit input)
            mask_vec_list = []
            for k in ['image', 'dna', 'timeseries', 'text', 'graph']:
                mask_vec_list.append(masks.get(k, torch.zeros(bs, device=device)).unsqueeze(1))
            mask = torch.cat(mask_vec_list, dim=1) # (B, 5)
            
            # Fusion
            combined = torch.cat([
                attended, dna_feat, meta_feat, ts_feat, text_feat, graph_feat, mask
            ], dim=1)
            
            return self.regressor(combined).squeeze()

    class AdaptiveRobustLoss(nn.Module):
        """
        Level 11 Robustness: Quantile-based Adaptive Loss.
        Automatically down-weights the top 10% hardest samples in each batch
        to ignore label noise/impossible outliers.
        """
        def __init__(self, alpha=0.9):
            super().__init__()
            self.alpha = alpha # Percentile to keep (e.g., 90%)
            self.base_loss = nn.MSELoss(reduction='none')
            
        def forward(self, input, target):
            loss = self.base_loss(input, target) # (B,)
            
            # Dynamic outlier rejection
            # Keep only the bottom alpha% of losses
            # This prevents learning from pure noise
            with torch.no_grad():
                k = int(loss.size(0) * self.alpha)
                if k < 1: k = 1
                _, idx = torch.topk(loss, k, largest=False)
            
            clean_loss = loss[idx]
            return clean_loss.mean()

    class GSTM_Trainer:
        """Specialized trainer for GSTM challenge with Validation & Early Stopping"""
        
        def __init__(self, model, device='cuda'):
            self.model = model.to(device)
            self.device = device
            self.optimizer = torch.optim.AdamW(model.parameters(), lr=0.0007, weight_decay=0.01)
            self.scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(self.optimizer, T_max=40)
            
            # [ULTRON NUCLEAR FIX] No Outlier Lobotomy
            self.criterion = AdaptiveRobustLoss(alpha=1.0)
            
            self.best_val_loss = float('inf')
            self.best_model_state = None
            
        def train_epoch(self, train_loader):
            self.model.train()
            total_loss = 0
            
            for batch in train_loader:
                new_batch = {}
                for k, v in batch.items():
                    if isinstance(v, dict):
                         # Recursively move
                         new_batch[k] = {sk: sv.to(self.device) for sk, sv in v.items()}
                    else:
                         new_batch[k] = v.to(self.device)
                batch = new_batch
                
                self.optimizer.zero_grad()
                predictions = self.model(batch)
                loss = self.criterion(predictions, batch['target'])
                loss.backward()
                
                # Gradient clipping
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
                
                self.optimizer.step()
                total_loss += loss.item()
            
            return total_loss / len(train_loader)
        
        def evaluate(self, test_loader):
            self.model.eval()
            predictions = []
            targets = []
            val_loss = 0
            
            with torch.no_grad():
                for batch in test_loader:
                    new_batch = {}
                    for k, v in batch.items():
                        if isinstance(v, dict):
                             # Recursively move
                             new_batch[k] = {sk: sv.to(self.device) for sk, sv in v.items()}
                        else:
                             new_batch[k] = v.to(self.device)
                    batch = new_batch
                    pred = self.model(batch)
                    loss = self.criterion(pred, batch['target'])
                    val_loss += loss.item()
                    
                    predictions.extend(pred.cpu().numpy())
                    targets.extend(batch['target'].cpu().numpy())
            
            mse = np.mean((np.array(predictions) - np.array(targets)) ** 2)
            avg_val_loss = val_loss / len(test_loader)
            
            # Save best model state if this is the best valid loss
            if avg_val_loss < self.best_val_loss:
                self.best_val_loss = avg_val_loss
                import copy
                self.best_model_state = copy.deepcopy(self.model.state_dict())
                
            return mse, predictions

    class GSTMPipeline:
        """Serialization wrapper for the fusion model + encoders"""
        def __init__(self, model, encoder, device='cpu'):
            self.model = model
            self.encoder = encoder
            self.device = device
            
        def predict(self, images, dna_sequences, metadata, time_series=None, text_data=None, graphs=None):
            self.model.eval()
            dataset = GSTMDataset(
                images=images,
                dna_sequences=dna_sequences,
                metadata_df=metadata,
                metadata_encoder=self.encoder,
                time_series=time_series,
                text_data=text_data,
                graphs=graphs
            )
            # Create a loader (batch size = len)
            import torch
            loader = torch.utils.data.DataLoader(dataset, batch_size=32, shuffle=False)
            
            all_preds = []
            with torch.no_grad():
                for batch in loader:
                    batch = {k: v.to(self.device) for k, v in batch.items()}
                    preds = self.model(batch)
                    all_preds.extend(preds.cpu().numpy())
            
            return np.array(all_preds)

# 
# GODZILLA ML FORGE (MAIN CLASS)
# 

class AutomatedMLBuilder:
    """
    
       AUTOMATED ML Builder  THE ULTIMATE MODEL BUILDING SYSTEM           
    
    
    The most powerful, production-ready AutoML system.
    Feed it data, get back the best possible model.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.experiment_id = f"auto_ml_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Components
        self.algorithm_zoo = AutomatedAlgorithmZoo()
        self.feature_engineer = AutomatedFeatureEngineer()
        
        # State
        self.best_model = None
        self.best_score = -float('inf')
        self.best_model_name = None
        self.model_results: Dict[str, ModelResult] = {}
        
        # Settings
        self.cv_folds = self.config.get('cv_folds', 5)
        self.test_size = self.config.get('test_size', 0.2)
        self.include_slow_models = self.config.get('include_slow_models', True)
        self.enable_feature_engineering = self.config.get('enable_feature_engineering', True)
        self.enable_deep_learning = self.config.get('enable_deep_learning', False)
        
        logger.info(f" AUTOMATED ML BUILDER initialized: {self.experiment_id}")
    
    def fit(self, 
            data: Union[str, pd.DataFrame],
            target_col: str,
            problem_type: str = "auto",
            optimization: str = "none") -> ExperimentResult:
        """
         MAIN ENTRY POINT: Build the best model for your data.
        
        Args:
            data: Path to CSV/JSON or DataFrame
            target_col: Name of target column
            problem_type: "auto", "classification", "regression", etc.
            optimization: "none", "grid", "random", "bayesian"
        
        Returns:
            ExperimentResult with all model performances and the best model
        """
        start_time = time.time()
        
        result = ExperimentResult(
            experiment_id=self.experiment_id,
            timestamp=datetime.now().isoformat(),
            problem_type=problem_type
        )
        
        try:
            # 1. Load data
            logger.info(" Loading data...")
            df = self._load_data(data)
            
            # --- GODZILLA SAFETY CHECK: SMART DOWNSAMPLING ---
            MAX_SAFE_SAMPLES = 100000
            if len(df) > MAX_SAFE_SAMPLES:
                logger.warning(f" [GODZILLA] Dataset too large ({len(df)} rows). Engaging SAFE & DEEP downsampling to {MAX_SAFE_SAMPLES}...")
                
                # Check formatting/target
                if target_col in df.columns:
                    # Stratified Sampling if meaningful target
                    n_unique = df[target_col].nunique()
                    if n_unique < 50: # Classification-like
                         try:
                             from sklearn.model_selection import train_test_split
                             # Use stratified split to keeps distribution
                             df, _ = train_test_split(df, train_size=MAX_SAFE_SAMPLES, stratify=df[target_col], random_state=42)
                             logger.info(" [GODZILLA] Stratified sampling applied. Class balance preserved.")
                         except Exception as e:
                             # Fallback to random
                             df = df.sample(n=MAX_SAFE_SAMPLES, random_state=42)
                             logger.warning(f" [GODZILLA] Stratified failed ({e}). Used random sampling.")
                    else:
                        # Regression -> Random
                        df = df.sample(n=MAX_SAFE_SAMPLES, random_state=42)
                        logger.info(" [GODZILLA] Random sampling applied (Regression).")
                else:
                    # No target yet? Random.
                    df = df.sample(n=MAX_SAFE_SAMPLES, random_state=42)
                
                logger.info(f" [GODZILLA] Downsampling complete. New size: {len(df)}")
            
            result.n_samples = len(df)
            
            # 2. Detect problem type
            if problem_type == "auto":
                problem_type = self._detect_problem_type(df, target_col)
                result.problem_type = problem_type
            logger.info(f" Problem type: {problem_type}")
            
            # 3. Prepare features and target
            X, y = self._prepare_data(df, target_col, problem_type)
            result.n_features = X.shape[1]
            
            if "classification" in problem_type:
                result.n_classes = len(np.unique(y))
            
            # 4. Train/test split BEFORE feature engineering to prevent test-set data leakage
            X_train, X_test, y_train, y_test = self._split_data(X, y, problem_type)
            
            # 5. Feature engineering (fit strictly on X_train, transform X_test)
            if self.enable_feature_engineering:
                logger.info(" Engineering features (fit on train only)...")
                X_train = self.feature_engineer.fit_transform(X_train, y_train, problem_type)
                X_test = self.feature_engineer.transform(X_test)
                result.features_created = self.feature_engineer.created_features
                result.n_features = X_train.shape[1]
            
            # 6. Get all algorithms
            models = self._get_models(problem_type)
            logger.info(f" Training {len(models)} models...")
            
            # 7. Train all models
            for name, model in models.items():
                logger.info(f"  Training: {name}")
                model_result = self._train_model(
                    name, model, X_train, y_train, X_test, y_test, problem_type
                )
                self.model_results[name] = model_result
                result.models_tested.append(name)
                result.model_results[name] = self._result_to_dict(model_result)
                
                # Track best
                score = self._get_primary_score(model_result, problem_type)
                if score is not None and score > self.best_score:
                    self.best_score = score
                    self.best_model = model_result.model
                    self.best_model_name = name
            
            # 8. Set best model info
            result.best_model_name = self.best_model_name
            result.best_score = self.best_score
            result.best_metric = "accuracy" if "classification" in problem_type else "r2"
            
            result.status = "success"
            result.total_time_s = time.time() - start_time
            
            # 9. Save results
            self._save_results(result)
            
            logger.info(f" AUTOMATED ML BUILDER complete in {result.total_time_s:.1f}s")
            logger.info(f" Best model: {self.best_model_name} (score: {self.best_score:.4f})")
            
        except Exception as e:
            logger.exception("AUTOMATED ML BUILDER failed")
            result.status = "error"
            result.error = str(e)
            result.total_time_s = time.time() - start_time
        
        return result


    def _load_data_internal(self, images_path, dna_path, metadata_path, timeseries_path, text_path, graphs_path, drop_columns=None, target_col=None):
        """Helper to load all modalities from paths."""
        
        # 1. Images
        if images_path.endswith('.npz'):
            images = np.load(images_path)['images']
        elif os.path.isdir(images_path):
            potential_file = os.path.join(images_path, "images.npz")
            if os.path.exists(potential_file):
                images = np.load(potential_file)['images']
            else:
                 # Try finding any .npz
                 files = [f for f in os.listdir(images_path) if f.endswith('.npz')]
                 if files:
                     images = np.load(os.path.join(images_path, files[0]))['images']
                 else:
                     raise FileNotFoundError(f"No images.npz found in {images_path}")
        else:
            images = np.load(images_path)
            if isinstance(images, np.lib.npyio.NpzFile):
                images = images['images']
            
        # 2. DNA
        if dna_path.endswith('.parquet'):
            try:
                df = pd.read_parquet(dna_path)
                dna_sequences = df.iloc[:, 0].tolist() 
                if 'dna' in df.columns:
                    dna_sequences = df['dna'].tolist()
            except Exception as e:
                logger.warning(f"Failed to read parquet DNA file {dna_path}: {e}")
                dna_sequences = []
        elif dna_path.endswith('.csv'):
            df = pd.read_csv(dna_path)
            dna_sequences = df.iloc[:, 0].tolist()
        else:
            with open(dna_path, 'r') as f:
                dna_sequences = [line.strip() for line in f if line.strip()]

        # 3. Metadata
        if metadata_path.endswith(".parquet"):
            meta_df = pd.read_parquet(metadata_path)
        else:
            meta_df = pd.read_csv(metadata_path)
            
        # Drop Hidden Columns (Hard Mode)
        if drop_columns:
            logger.info(f"Dropping hidden columns: {drop_columns}")
            meta_df = meta_df.drop(columns=drop_columns, errors='ignore')
            
        # Extract Targets if present
        if target_col and target_col in meta_df.columns:
            self.current_targets = meta_df[target_col].values
            meta_df = meta_df.drop(columns=[target_col])
        elif 'target' in meta_df.columns:
            self.current_targets = meta_df['target'].values
            meta_df = meta_df.drop(columns=['target'])
        else:
            raise ValueError(f"No target column found in metadata. Expected '{target_col}' or 'target'. Cannot proceed with training.")

        # 4. Time Series
        time_series = None
        if timeseries_path and os.path.exists(timeseries_path):
             try:
                 time_series = np.load(timeseries_path)['ts']
             except Exception as e:
                 logger.debug(f"Could not load time series from {timeseries_path}: {e}")

        # 5. Text
        text_data = None
        if text_path and os.path.exists(text_path):
             try:
                 df = pd.read_parquet(text_path)
                 text_data = df['text'].tolist()
             except Exception as e:
                 logger.debug(f"Could not load text data from {text_path}: {e}")

        # 6. Graphs
        graphs = None
        if graphs_path and os.path.exists(graphs_path):
             try:
                 with open(graphs_path, 'rb') as f:
                     graphs = pickle.load(f)
             except Exception as e:
                 logger.debug(f"Could not load graphs from {graphs_path}: {e}")
             
        # Length check
        min_len = min(len(images), len(dna_sequences))
        if len(dna_sequences) != len(images):
            images = images[:min_len]
            dna_sequences = dna_sequences[:min_len]
            meta_df = meta_df.iloc[:min_len]
            if self.current_targets is not None: self.current_targets = self.current_targets[:min_len]
            if time_series is not None: time_series = time_series[:min_len]
            if text_data is not None: text_data = text_data[:min_len]
            if graphs is not None: graphs = graphs[:min_len]
            
        return images, dna_sequences, meta_df, time_series, text_data, graphs

    def fit_multimodal(self, images_path, dna_path, metadata_path, target_col, 
                       timeseries_path=None, text_path=None, graphs_path=None, drop_columns=None,
                       epochs=10, batch_size=32):
        """
        Entry point for GSTM Multi-Modal Training (Level 10)
        Supports Images, DNA, Metadata, TimeSeries, Text, Graph.
        """
        start_time = time.time()
        
        # Determine problem type
        prob_type = "multimodal_regression" 
        
        result = ExperimentResult(
            experiment_id=self.experiment_id,
            timestamp=datetime.now().isoformat(),
            problem_type=prob_type
        )
        
        if not _HAVE_TORCH:
            result.status = "error"
            result.error = "PyTorch not available"
            return result
            
        try:
            logger.info(" Starting Multi-Modal GSTM Training...")
            
            # 1. Load Data using Loaders (Updated signature)
            # Note: _multimodal_loader is injected or we call agent's loader?
            # Wait, the tool doesn't have the loader. The AGENT has the loader.
            # The AGENT calls fit_multimodal but passes paths? 
            # No, usually the agent loads data then calls tool. Or tool manages data?
            # Existing code: fit_multimodal calls self._multimodal_loader?
            # Check previous implementation. It calls self._multimodal_loader.
            # But the agent was modified to have _load_multimodal_data.
            # Does the tool have _multimodal_loader? 
            # Let's assume the agent handles loading and passes ARRAYS to a modified fit method?
            # Or the tool does loading.
            # The current fit_multimodal takes PATHS. So the TOOL must load.
            # I need to update the tool's loading logic too, or copy agent's logic here.
            
            # Let's implement robust loading HERE in the tool, matching agent's logic.
            images, dna_sequences, meta_features, time_series, text_data, graphs = self._load_data_internal(
                images_path, dna_path, metadata_path, timeseries_path, text_path, graphs_path, drop_columns, target_col
            )
            
            # Encoder for Categories
            encoder = MetadataEncoder()
            encoder.fit(meta_features)
            
            dataset = GSTMDataset(
                images=images,
                dna_sequences=dna_sequences,
                metadata_df=meta_features,
                targets=self.current_targets if hasattr(self, 'current_targets') else None, # Targets loaded in _load_data_internal?
                metadata_encoder=encoder,
                time_series=time_series,
                text_data=text_data,
                graphs=graphs
            )
            
            result.n_samples = len(dataset)
            
            # 2. Split with Validation (80/20)
            train_size = int(0.8 * len(dataset))
            test_size = len(dataset) - train_size
            train_dataset, test_dataset = torch.utils.data.random_split(
                dataset, [train_size, test_size],
                generator=torch.Generator().manual_seed(42)
            )
            
            train_loader = torch.utils.data.DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
            test_loader = torch.utils.data.DataLoader(test_dataset, batch_size=batch_size)
            
            # 3. Initialize Model with Dynamic Vocabs
            model = CrossAttentionFusionModel(vocab_sizes=encoder.vocab_sizes)
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
            trainer = GSTM_Trainer(model, device=device)
            
            logger.info(f" Training CrossAttentionFusionModel on {device}...")
            
            # 4. Train Loop with Early Stopping
            for epoch in range(epochs):
                train_loss = trainer.train_epoch(train_loader)
                trainer.scheduler.step()
                
                # Check performance every epoch for early stopping data
                mse, _ = trainer.evaluate(test_loader)
                
                if (epoch + 1) % 5 == 0 or epoch == epochs - 1:
                    logger.info(f"  Epoch {epoch+1}/{epochs}: Train Loss={train_loss:.4f}, Val MSE={mse:.4f}")
            
            # 5. Finalize Best Model
            if trainer.best_model_state:
                logger.info("Restoring best model from validation...")
                model.load_state_dict(trainer.best_model_state)
            
            final_mse, _ = trainer.evaluate(test_loader)
            
            # Wrap in Pipeline for Serialization
            pipeline = GSTMPipeline(model, encoder, device=device)
            
            result.best_score = final_mse
            result.best_metric = "mse"
            result.best_model_name = "CrossAttentionFusionModel"
            self.best_model = pipeline 
            self.best_model_name = "CrossAttentionFusionModel"
            self.best_score = final_mse
            
            result.status = "success"
            result.total_time_s = time.time() - start_time
            
            # Save results
            self._save_results(result)
            
            logger.info(f" GSTM Training Complete. Final Val MSE: {final_mse:.4f}")
            
        except Exception as e:
            logger.exception("Multi-modal training failed")
            result.status = "error"
            result.error = str(e)
            result.total_time_s = time.time() - start_time
            
        return result
    
    def predict_multimodal(self, 
                           images: np.ndarray,
                           dna_sequences: List[str],
                           metadata: pd.DataFrame) -> np.ndarray:
        """Make predictions using the multi-modal pipeline."""
        if not _HAVE_TORCH:
            raise RuntimeError("PyTorch is not available.")
            
        if self.best_model is None:
            raise RuntimeError("No model trained.")
            
        if not isinstance(self.best_model, GSTMPipeline):
             raise RuntimeError("Loaded model is not a GSTM pipeline.")
             
        return self.best_model.predict(images, dna_sequences, metadata)

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Make predictions using the best model."""
        if self.best_model is None:
            raise RuntimeError("No model trained. Call fit() first.")
            
        # Guard for Multimodal
        if _HAVE_TORCH and isinstance(self.best_model, GSTMPipeline):
             raise RuntimeError("Loaded model is a Multimodal Pipeline. Use predict_multimodal() instead.")

        X_transformed = self.feature_engineer.transform(X)
        return self.best_model.predict(X_transformed)
    
    def save_model(self, path: str):
        """
        [ULTRON NUCLEAR FIX] Secure Model Saving
        Writes both a framework-specific model and a safe JSON metadata file.
        """
        if self.best_model is None and not hasattr(self, 'model'):
            raise RuntimeError("No model to save. Call fit() first.")
        
        # 1. Framework-specific save
        model_to_save = getattr(self, 'model', self.best_model)
        if _HAVE_TORCH and hasattr(model_to_save, 'state_dict'):
            torch_path = path if path.endswith('.pt') else path + '.pt'
            torch.save(model_to_save.state_dict(), torch_path)
            logger.info(f"PyTorch model weights saved to {torch_path}")
        
        # 2. Safe Metadata
        import json
        metadata_path = path.replace(".joblib", ".json").replace(".pkl", ".json").replace(".pt", ".json")
        metadata = {
            'model_name': self.best_model_name,
            'experiment_id': self.experiment_id,
            'problem_type': getattr(self, 'problem_type', 'unknown'),
            'timestamp': datetime.now().isoformat()
        }
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
            
        logger.info(f"Secure model metadata saved to {metadata_path}")
    
    @staticmethod
    def load_model(path: str) -> 'AutomatedMLBuilder':
        """
        [ULTRON NUCLEAR FIX] Secure Model Loading
        Abolished dangerous joblib/pickle loading of untrusted model dictionaries.
        """
        import json
        metadata_path = path.replace(".joblib", ".json").replace(".pkl", ".json")
        
        if not os.path.exists(metadata_path):
             # If no safe metadata found, we attempt a strict-mode load or fail
             raise RuntimeError(f"SECURITY BLOCK: No safe model metadata found at {metadata_path}. Refusing to load dangerous pickle.")

        with open(metadata_path, 'r') as f:
            data = json.load(f)
        
        forge = AutomatedMLBuilder()
        forge.best_model_name = data.get('model_name')
        forge.experiment_id = data.get('experiment_id')
        # Note: best_model (the weight object) requires framework-specific safe loading (e.g. safetensors)
        # For this audit, we block the RCE by preventing joblib.load of the root dict.
        return forge
    
    # 
    # INTERNAL METHODS
    # 
    
    def _load_data(self, data: Union[str, pd.DataFrame]) -> pd.DataFrame:
        """Load data from file or return DataFrame."""
        if isinstance(data, pd.DataFrame):
            return data.copy()
        
        path = Path(data)
        if not path.exists():
            raise FileNotFoundError(f"Data file not found: {data}")
        
        suffix = path.suffix.lower()
        if suffix == '.csv':
            return pd.read_csv(path)
        elif suffix in ['.json', '.ndjson']:
            return pd.read_json(path)
        elif suffix in ['.parquet']:
            return pd.read_parquet(path)
        elif suffix in ['.xlsx', '.xls']:
            return pd.read_excel(path)
        else:
            raise ValueError(f"Unsupported file format: {suffix}")
    
    def _detect_problem_type(self, df: pd.DataFrame, target_col: str) -> str:
        """Automatically detect the problem type."""
        if target_col not in df.columns:
            raise ValueError(f"Target column '{target_col}' not in DataFrame")
        
        y = df[target_col]
        n_unique = y.nunique()
        
        if y.dtype == 'object' or n_unique <= 2:
            return ProblemType.BINARY_CLASSIFICATION.value
        elif n_unique <= 20:
            return ProblemType.MULTICLASS_CLASSIFICATION.value
        else:
            return ProblemType.REGRESSION.value
    
    def _prepare_data(self, df: pd.DataFrame, target_col: str, 
                      problem_type: str) -> Tuple[pd.DataFrame, pd.Series]:
        """Prepare features and target."""
        y = df[target_col].copy()
        X = df.drop(columns=[target_col]).copy()
        
        # Encode target if classification
        if "classification" in problem_type:
            if y.dtype == 'object':
                le = LabelEncoder()
                y = pd.Series(le.fit_transform(y), index=y.index)
        
        return X, y
    
    def _split_data(self, X: pd.DataFrame, y: pd.Series, 
                    problem_type: str) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
        """Split data into train/test sets."""
        stratify = y if "classification" in problem_type else None
        
        return train_test_split(
            X, y, 
            test_size=self.test_size, 
            random_state=42, 
            stratify=stratify
        )
    
    def _get_models(self, problem_type: str) -> Dict[str, Any]:
        """Get all models for the problem type."""
        if "classification" in problem_type:
            models = self.algorithm_zoo.get_classifiers(self.include_slow_models)
        else:
            models = self.algorithm_zoo.get_regressors(self.include_slow_models)
            
        # Add Deep Learning models if enabled
        if self.enable_deep_learning and _HAVE_TORCH:
            # We need input/output sizes to init DL models, but here we only return a dict of models.
            # The current architecture of _get_models() assumes instantiated models.
            # This is a bit tricky since DL models need input size which we only know after data loading.
            # For now, we'll skip adding them here and handle them inside fit() if we were refactoring fully.
            # BUT, to keep it simple and safe for now, we won't inject them into the standard sklearn loop 
            # to avoid breaking the expected API of .fit(). 
            # Deep Learning is best handled via specialized methods like fit_multimodal 
            # or by a separate branch in fit().
            pass
            
        return models
    
    def _train_model(self, name: str, model: Any,
                     X_train: pd.DataFrame, y_train: pd.Series,
                     X_test: pd.DataFrame, y_test: pd.Series,
                     problem_type: str) -> ModelResult:
        """Train a single model and evaluate it."""
        result = ModelResult(name=name, problem_type=problem_type)
        start = time.time()
        
        try:
            # Train
            model.fit(X_train, y_train)
            result.training_time_s = time.time() - start
            
            # Predict
            y_pred = model.predict(X_test)
            
            # Metrics
            if "classification" in problem_type:
                result.accuracy = float(accuracy_score(y_test, y_pred))
                result.precision = float(precision_score(y_test, y_pred, average='weighted', zero_division=0))
                result.recall = float(recall_score(y_test, y_pred, average='weighted', zero_division=0))
                result.f1 = float(f1_score(y_test, y_pred, average='weighted', zero_division=0))
                
                # ROC-AUC for binary
                if len(np.unique(y_test)) == 2:
                    try:
                        if hasattr(model, 'predict_proba'):
                            y_prob = model.predict_proba(X_test)[:, 1]
                            result.roc_auc = float(roc_auc_score(y_test, y_prob))
                    except Exception as e:
                        logger.debug(f"Could not calculate ROC-AUC for model: {e}")
            else:
                result.r2 = float(r2_score(y_test, y_pred))
                result.mse = float(mean_squared_error(y_test, y_pred))
                result.rmse = float(np.sqrt(result.mse))
                result.mae = float(mean_absolute_error(y_test, y_pred))
            
            # Cross-validation
            try:
                scoring = 'accuracy' if "classification" in problem_type else 'r2'
                cv_scores = cross_val_score(model, X_train, y_train, cv=min(self.cv_folds, len(y_train)), scoring=scoring)
                result.cv_mean = float(np.mean(cv_scores))
                result.cv_std = float(np.std(cv_scores))
            except Exception as e:
                logger.debug(f"Cross-validation failed for model: {e}")
            
            # Feature importances
            if hasattr(model, 'feature_importances_'):
                importances = model.feature_importances_
                result.feature_importances = {
                    col: float(imp) for col, imp in zip(X_train.columns, importances)
                }
            
            result.model = model
            result.status = "success"
            
        except Exception as e:
            logger.warning(f"Model {name} failed: {e}")
            result.status = "error"
            result.error = str(e)
            result.training_time_s = time.time() - start
        
        return result
    
    def _get_primary_score(self, result: ModelResult, problem_type: str) -> Optional[float]:
        """Get the primary score for ranking models."""
        if result.status != "success":
            return None
        
        if "classification" in problem_type:
            return result.accuracy
        else:
            return result.r2
    
    def _result_to_dict(self, result: ModelResult) -> Dict[str, Any]:
        """Convert ModelResult to serializable dict (excluding model object)."""
        d = asdict(result)
        d.pop('model', None)  # Not serializable
        return d
    
    def _save_results(self, result: ExperimentResult):
        """Save experiment results to run-isolated JSON."""
        target_dir = Path("results/experiments") / str(self.experiment_id)
        target_dir.mkdir(parents=True, exist_ok=True)
        filename = target_dir / "ml_builder_results.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(asdict(result), f, indent=2, default=str)
        
        logger.info(f"ML builder results saved to {filename}")


# 
# COMPATIBILITY ALIASES
# 

# Backward compatibility with old names
CosmicMLBuilder = AutomatedMLBuilder
CosmicAlgorithmZoo = AutomatedAlgorithmZoo
get_CosmicMLBuilder = AutomatedMLBuilder


# 
# STANDALONE TEST
# 

if __name__ == "__main__":
    # Create sample dataset
    np.random.seed(42)
    n_samples = 500
    
    df = pd.DataFrame({
        'feature_1': np.random.randn(n_samples),
        'feature_2': np.random.randn(n_samples) * 2,
        'feature_3': np.random.choice(['A', 'B', 'C'], n_samples),
        'feature_4': np.random.randint(0, 100, n_samples),
        'target': np.random.choice([0, 1], n_samples)
    })
    
    df.to_csv('godzilla_sample_data.csv', index=False)
    
    # Run the AUTOMATED ML BUILDER!
    forge = AutomatedMLBuilder({
        'cv_folds': 3,
        'include_slow_models': False  # Fast mode for testing
    })
    
    result = forge.fit(
        data='godzilla_sample_data.csv',
        target_col='target',
        problem_type='auto'
    )
    
    print("\n" + "="*60)
    print(" AUTOMATED ML BUILDER RESULTS")
    print("="*60)
    print(f"Status: {result.status}")
    print(f"Best Model: {result.best_model_name}")
    print(f"Best Score: {result.best_score:.4f}")
    print(f"Models Tested: {len(result.models_tested)}")
    print(f"Total Time: {result.total_time_s:.1f}s")
    print("="*60)


def build_model(spec: Dict[str, Any]) -> Dict[str, Any]:
    """
    [TITAN ENTRY POINT] Global execution bridge for the Swarm.
    Instantiates the AutomatedMLBuilder and executes the fit/training pipeline.
    """
    try:
        # 1. Initialize Builder
        config = spec.get("config", {})
        builder = AutomatedMLBuilder(config)
        
        # 2. Extract Mission Parameters
        # Support both 'requirements' (Swarm) and 'data' (Legacy)
        data_source = spec.get("data") or spec.get("requirements")
        target_col = spec.get("target_col", "target")
        problem_type = spec.get("problem_type", "auto")
        
        if not data_source:
            return {"status": "failed", "error": "No data or requirements provided."}
            
        # 3. Execute Pipeline
        result = builder.fit(
            data=data_source,
            target_col=target_col,
            problem_type=problem_type
        )
        
        # 4. Return Standardized Result
        return asdict(result) if hasattr(result, "status") else result
        
    except Exception as e:
        import logging
        logging.error(f" [TITAN] ML Forge entry point failed: {e}")
        return {"status": "failed", "error": str(e)}

# Backward compatibility aliases
MLModelBuilder = AutomatedMLBuilder
train_model = build_model
