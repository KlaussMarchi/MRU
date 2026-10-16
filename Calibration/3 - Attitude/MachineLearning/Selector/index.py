from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression, Ridge, Lasso, ElasticNet
from sklearn.neighbors import KNeighborsRegressor
from sklearn.svm import SVR
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.tree import DecisionTreeRegressor
from sklearn.multioutput import MultiOutputRegressor

from scipy.stats import loguniform, uniform, randint
import warnings
from sklearn.exceptions import ConvergenceWarning
warnings.filterwarnings("ignore", category=ConvergenceWarning)

SINGLE_OUTPUT = ['svr', 'gradient_boosting']    # SÓ ACEITAM UM y: COM MAIS SAÍDAS VIRAM UM MODELO POR SAÍDA


class ModelSelector:
    options = {
        'linear_regression': {
            'model': LinearRegression(),
            'needs_scaling': True,
            'params': {
                'fit_intercept': [True, False],
                'positive': [True, False]
            }
        },
        'ridge': {
            'model': Ridge(random_state=42),
            'needs_scaling': True,
            'params': {
                'alpha': loguniform(1e-3, 1e3),
                'solver': ['auto', 'svd', 'cholesky', 'lsqr', 'sag']
            }
        },
        'lasso': {
            'model': Lasso(random_state=42),
            'needs_scaling': True,
            'params': {
                'alpha': loguniform(1e-4, 1e2),
                'selection': ['cyclic', 'random']
            }
        },
        'elastic_net': {
            'model': ElasticNet(random_state=42),
            'needs_scaling': True,
            'params': {
                'alpha': loguniform(1e-4, 1e2),
                'l1_ratio': uniform(0.01, 0.98)
            }
        },
        'knn': {
            'model': KNeighborsRegressor(),
            'needs_scaling': True,
            'params': {
                'n_neighbors': randint(2, 20),
                'weights': ['uniform', 'distance'],
                'metric': ['euclidean', 'manhattan']
            }
        },
        'svr': {
            'model': SVR(),
            'needs_scaling': True,
            'params': {
                'C': loguniform(1e-3, 1e2),
                'kernel': ['rbf', 'linear', 'poly'],
                'gamma': ['scale', 'auto'],
                'epsilon': loguniform(1e-3, 1e1)
            }
        },
        'random_forest': {
            'model': RandomForestRegressor(random_state=42),
            'needs_scaling': False,
            'params': {
                'n_estimators': randint(100, 600),
                'max_depth': randint(5, 50),
                'min_samples_split': randint(2, 15),
                'min_samples_leaf': randint(1, 10)
            }
        },
        'gradient_boosting': {
            'model': GradientBoostingRegressor(random_state=42),
            'needs_scaling': False,
            'params': {
                'n_estimators': randint(100, 500),
                'learning_rate': loguniform(1e-3, 5e-1),
                'max_depth': randint(3, 10),
                'loss': ['squared_error', 'huber', 'absolute_error']
            }
        },
        'decision_tree': {
            'model': DecisionTreeRegressor(random_state=42),
            'needs_scaling': False,
            'params': {
                'criterion': ['squared_error', 'friedman_mse', 'absolute_error'],
                'max_depth': randint(5, 50),
                'min_samples_split': randint(2, 15)
            }
        }
    }

    def __init__(self, name: str, n_outputs=1):
        self.chosen = name
        self.selected = self.options[name]
        self.n_outputs = n_outputs

    def get(self):
        base_model = self.selected['model']
        raw_params = self.selected['params']

        if self.chosen in SINGLE_OUTPUT and self.n_outputs > 1:
            base_model = MultiOutputRegressor(base_model)
            raw_params = {f'estimator__{k}': v for k, v in raw_params.items()}

        if self.selected['needs_scaling']:
            model = Pipeline([
                ('scaler', StandardScaler()), 
                ('model', base_model)
            ])
            params = {f'model__{k}': v for k, v in raw_params.items()}
        else:
            model = base_model
            params = raw_params
            
        return model, params