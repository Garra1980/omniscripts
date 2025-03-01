# coding: utf-8
import numpy as np
from sklearn import config_context
import warnings
from timeit import default_timer as timer

from utils import (
    check_support,
    cod,
    import_pandas_into_module_namespace,
    load_data_pandas,
    load_data_modin_on_omnisci,
    mse,
    print_results,
    split,
    getsize,
)

warnings.filterwarnings("ignore")


# Dataset link
# https://rapidsai-data.s3.us-east-2.amazonaws.com/datasets/ipums_education2income_1970-2010.csv.gz


def etl(filename, columns_names, columns_types, etl_keys, pandas_mode):
    etl_times = {key: 0.0 for key in etl_keys}

    t0 = timer()
    if pandas_mode == "Modin_on_omnisci":
        df = load_data_modin_on_omnisci(
            filename=filename,
            columns_names=columns_names,
            columns_types=columns_types,
            skiprows=1,
            pd=run_benchmark.__globals__["pd"],
        )
    else:
        df = load_data_pandas(
            filename=filename,
            columns_names=columns_names,
            columns_types=columns_types,
            header=0,
            nrows=None,
            use_gzip=filename.endswith(".gz"),
            pd=run_benchmark.__globals__["pd"],
        )
    etl_times["t_readcsv"] = timer() - t0

    t_etl_start = timer()

    keep_cols = [
        "YEAR0",
        "DATANUM",
        "SERIAL",
        "CBSERIAL",
        "HHWT",
        "CPI99",
        "GQ",
        "PERNUM",
        "SEX",
        "AGE",
        "INCTOT",
        "EDUC",
        "EDUCD",
        "EDUC_HEAD",
        "EDUC_POP",
        "EDUC_MOM",
        "EDUCD_MOM2",
        "EDUCD_POP2",
        "INCTOT_MOM",
        "INCTOT_POP",
        "INCTOT_MOM2",
        "INCTOT_POP2",
        "INCTOT_HEAD",
        "SEX_HEAD",
    ]
    df = df[keep_cols]

    df = df[df["INCTOT"] != 9999999]
    df = df[df["EDUC"] != -1]
    df = df[df["EDUCD"] != -1]

    df["INCTOT"] = df["INCTOT"] * df["CPI99"]

    for column in keep_cols:
        df[column] = df[column].fillna(-1)

        df[column] = df[column].astype("float64")

    y = df["EDUC"]
    X = df.drop(columns=["EDUC", "CPI99"])

    # trigger computation
    df.shape
    y.shape
    X.shape

    etl_times["t_etl"] = timer() - t_etl_start
    print("DataFrame shape:", X.shape)

    return df, X, y, etl_times


def ml(X, y, random_state, n_runs, test_size, optimizer, ml_keys, ml_score_keys):
    if optimizer == "intel":
        print("Intel optimized sklearn is used")
        import sklearnex.linear_model as lm
    elif optimizer == "stock":
        print("Stock sklearn is used")
        import sklearn.linear_model as lm
    else:
        raise NotImplementedError(
            f"{optimizer} is not implemented, accessible optimizers are 'stcok' and 'intel'"
        )

    clf = lm.Ridge()

    X = np.ascontiguousarray(X, dtype=np.float64)
    y = np.ascontiguousarray(y, dtype=np.float64)

    mse_values, cod_values = [], []
    ml_times = {key: 0.0 for key in ml_keys}
    ml_scores = {key: 0.0 for key in ml_score_keys}

    print("ML runs: ", n_runs)
    for i in range(n_runs):
        (X_train, y_train, X_test, y_test), split_time = split(
            X, y, test_size=test_size, random_state=random_state, optimizer=optimizer
        )
        ml_times["t_train_test_split"] += split_time
        random_state += 777

        t0 = timer()
        with config_context(assume_finite=True):
            model = clf.fit(X_train, y_train)
        ml_times["t_train"] += timer() - t0

        t0 = timer()
        y_pred = model.predict(X_test)
        ml_times["t_inference"] += timer() - t0

        mse_values.append(mse(y_test, y_pred))
        cod_values.append(cod(y_test, y_pred))

    ml_times["t_ml"] += ml_times["t_train"] + ml_times["t_inference"]

    ml_scores["mse_mean"] = sum(mse_values) / len(mse_values)
    ml_scores["cod_mean"] = sum(cod_values) / len(cod_values)
    ml_scores["mse_dev"] = pow(
        sum([(mse_value - ml_scores["mse_mean"]) ** 2 for mse_value in mse_values])
        / (len(mse_values) - 1),
        0.5,
    )
    ml_scores["cod_dev"] = pow(
        sum([(cod_value - ml_scores["cod_mean"]) ** 2 for cod_value in cod_values])
        / (len(cod_values) - 1),
        0.5,
    )

    return ml_scores, ml_times


def run_benchmark(parameters):
    check_support(parameters, unsupported_params=["dfiles_num", "gpu_memory"])

    parameters["data_file"] = parameters["data_file"].replace("'", "")
    parameters["optimizer"] = parameters["optimizer"] or "intel"
    parameters["no_ml"] = parameters["no_ml"] or False

    # ML specific
    N_RUNS = 50
    TEST_SIZE = 0.1
    RANDOM_STATE = 777

    columns_names = [
        "YEAR0",
        "DATANUM",
        "SERIAL",
        "CBSERIAL",
        "HHWT",
        "CPI99",
        "GQ",
        "QGQ",
        "PERNUM",
        "PERWT",
        "SEX",
        "AGE",
        "EDUC",
        "EDUCD",
        "INCTOT",
        "SEX_HEAD",
        "SEX_MOM",
        "SEX_POP",
        "SEX_SP",
        "SEX_MOM2",
        "SEX_POP2",
        "AGE_HEAD",
        "AGE_MOM",
        "AGE_POP",
        "AGE_SP",
        "AGE_MOM2",
        "AGE_POP2",
        "EDUC_HEAD",
        "EDUC_MOM",
        "EDUC_POP",
        "EDUC_SP",
        "EDUC_MOM2",
        "EDUC_POP2",
        "EDUCD_HEAD",
        "EDUCD_MOM",
        "EDUCD_POP",
        "EDUCD_SP",
        "EDUCD_MOM2",
        "EDUCD_POP2",
        "INCTOT_HEAD",
        "INCTOT_MOM",
        "INCTOT_POP",
        "INCTOT_SP",
        "INCTOT_MOM2",
        "INCTOT_POP2",
    ]
    columns_types = [
        "int64",
        "int64",
        "int64",
        "float64",
        "int64",
        "float64",
        "int64",
        "float64",
        "int64",
        "int64",
        "int64",
        "int64",
        "int64",
        "int64",
        "int64",
        "float64",
        "float64",
        "float64",
        "float64",
        "float64",
        "float64",
        "float64",
        "float64",
        "float64",
        "float64",
        "float64",
        "float64",
        "float64",
        "float64",
        "float64",
        "float64",
        "float64",
        "float64",
        "float64",
        "float64",
        "float64",
        "float64",
        "float64",
        "float64",
        "float64",
        "float64",
        "float64",
        "float64",
        "float64",
        "float64",
    ]
    etl_keys = ["t_readcsv", "t_etl", "t_connect"]
    ml_keys = ["t_train_test_split", "t_ml", "t_train", "t_inference"]

    ml_score_keys = ["mse_mean", "cod_mean", "mse_dev", "cod_dev"]

    import_pandas_into_module_namespace(
        namespace=run_benchmark.__globals__,
        mode=parameters["pandas_mode"],
        ray_tmpdir=parameters["ray_tmpdir"],
        ray_memory=parameters["ray_memory"],
    )

    etl_times = None
    ml_times = None

    if parameters["data_file"].endswith(".csv"):
        csv_size = getsize(parameters["data_file"])
    else:
        print("WARNING: uncompressed datafile not found, default value for dataset_size is set")
        # deafault csv_size value (unit - MB) obtained by calling getsize
        # function on the ipums_education2income_1970-2010.csv file
        # (default Census benchmark data file)
        csv_size = 2100.0

    df, X, y, etl_times = etl(
        parameters["data_file"],
        columns_names=columns_names,
        columns_types=columns_types,
        etl_keys=etl_keys,
        pandas_mode=parameters["pandas_mode"],
    )

    print_results(results=etl_times, backend=parameters["pandas_mode"], unit="s")
    etl_times["Backend"] = parameters["pandas_mode"]
    etl_times["dataset_size"] = csv_size

    if not parameters["no_ml"]:
        ml_scores, ml_times = ml(
            X=X,
            y=y,
            random_state=RANDOM_STATE,
            n_runs=N_RUNS,
            test_size=TEST_SIZE,
            optimizer=parameters["optimizer"],
            ml_keys=ml_keys,
            ml_score_keys=ml_score_keys,
        )
        print_results(results=ml_times, backend=parameters["pandas_mode"], unit="s")
        ml_times["Backend"] = parameters["pandas_mode"]
        print_results(results=ml_scores, backend=parameters["pandas_mode"])
        ml_scores["Backend"] = parameters["pandas_mode"]

    return {"ETL": [etl_times], "ML": [ml_times]}
