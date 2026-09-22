from sklearn.model_selection import RandomizedSearchCV
from sklearn.base import clone
from sklearn.metrics import r2_score
from Metrics.CrossValidation.index import getSplitter

class RandomSearch:
    def __init__(self, model, params, xData, yData, k=5, n_iter=10, temporal=True):
        self.model = clone(model)
        self.params = params
        self.xData = xData
        self.yData = yData
        self.k = k
        self.n_iter = n_iter
        self.temporal = temporal
        self.search = None

    def update(self):
        train, test = next(getSplitter(len(self.yData), self.k, self.temporal).split(self.xData))    # HOLDOUT DE 1/k COM BALANÇO E REPOUSO
        self.xTrain, self.xTest = self.xData.iloc[train], self.xData.iloc[test]
        self.yTrain, self.yTest = self.yData.iloc[train], self.yData.iloc[test]

        cv_splitter = getSplitter(len(train), self.k, self.temporal)

        self.search = RandomizedSearchCV(
            estimator=self.model, 
            param_distributions=self.params,
            n_iter=self.n_iter,
            cv=cv_splitter, 
            scoring='r2', 
            n_jobs=-1, 
            verbose=1,
            random_state=42,
            return_train_score=False
        )
        
        self.search.fit(self.xTrain, self.yTrain)

    def evaluate(self):
        best_model = self.search.best_estimator_
        yPred = best_model.predict(self.xTest)
        
        r2 = r2_score(self.yTest, yPred)
        n = len(self.yTest)
        p = self.xTest.shape[1]
        
        r2_adj = 1 - (1 - r2) * (n - 1) / (n - p - 1) if n > p + 1 else r2 
        return best_model, r2_adj