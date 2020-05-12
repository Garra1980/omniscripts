# coding: utf-8
import os
import sys
import time
import traceback
import warnings
from timeit import default_timer as timer
import gc

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from utils import (
    check_fragments_size,
    cod,
    compare_dataframes,
    import_pandas_into_module_namespace,
    load_data_pandas,
    mse,
    print_results,
    make_chk,
    memory_usage,
)

warnings.filterwarnings("ignore")

# "Groupby with lists of columns not yet supported."
def q1_modin(x, queries_results):
    question = "sum v1 by id1" #1
    gc.collect()
    t_start = timer()
    ans = x.groupby(['id1']).agg({'v1':'sum'})
    print(ans.shape)
    queries_results["query1_run1_t"] = timer() - t_start
    m = memory_usage()
    t_start = timer()
    chk = [ans['v1'].sum()]
    queries_results["query1_run1_chk_t"] = timer() - t_start
    chk=make_chk(chk)
    print("query1, question:", question, ",run1", ",in_rows:", x.shape[0], ",out_rows:", ans.shape[0], ",out_cols:", ans.shape[1], ",time_sec:", queries_results["query1_run1_t"], "mem_gb:", m, ",chk:", chk , ",chk_time_sec:", queries_results["query1_run1_chk_t"])
    del ans
    gc.collect()

    t_start = timer()
    ans = x.groupby(['id1']).agg({'v1':'sum'})
    print(ans.shape)
    queries_results["query1_run2_t"] = timer() - t_start
    m = memory_usage()
    t_start = timer()
    chk = [ans['v1'].sum()]
    queries_results["query1_run2_chk_t"] = timer() - t_start
    chk=make_chk(chk)
    print("query1, question:", question, ",run2", ",in_rows:", x.shape[0], ",out_rows:", ans.shape[0], ",out_cols:", ans.shape[1], ",time_sec:", queries_results["query1_run2_t"], "mem_gb:", m, ",chk:", chk , ",chk_time_sec:", queries_results["query1_run2_chk_t"])
    del ans


def queries_modin(filename):
    queries = {
        "query1": q1_modin,
        # "Query2": q2_pandas,
        # "Query3": q3_pandas,
        # "Query4": q4_pandas,
    }
    queries_results = {x + "_run1_t": 0.0 for x in queries.keys()}
    queries_results.update({x + "_run2_t": 0.0 for x in queries.keys()})
    queries_results.update({x + "_run1_chk_t": 0.0 for x in queries.keys()})
    queries_results.update({x + "_run2_chk_t": 0.0 for x in queries.keys()})

    print(f"loading dataset {filename}")
    t0 = timer()
    x = pd.read_csv(filename)
    queries_results["t_readcsv"] = timer() - t0
    queries_results["dataset_size"] = os.path.getsize(filename) / 1024 /1024

    queries_parameters = {"x": x, "queries_results": queries_results}
    for query_name, query_func in queries.items():
        query_func(**queries_parameters)

    return queries_results


def run_benchmark(parameters):
    ignored_parameters = {
        "dfiles_num": parameters["dfiles_num"],
        "gpu_memory": parameters["gpu_memory"],
        "no_ml": parameters["no_ml"],
        "no_ibis": parameters["no_ibis"],
        "optimizer": parameters["optimizer"],
        "validation": parameters["validation"],
    }
    warnings.warn(f"Parameters {ignored_parameters} are irnored", RuntimeWarning)

    parameters["data_file"] = parameters["data_file"].replace("'", "")

    queries_times_modin = None

    try:
        if not parameters["no_pandas"]:
            import_pandas_into_module_namespace(
                namespace=run_benchmark.__globals__,
                mode=parameters["pandas_mode"],
                ray_tmpdir=parameters["ray_tmpdir"],
                ray_memory=parameters["ray_memory"],
            )
            queries_results = queries_modin(filename=parameters["data_file"])
            print_results(results=queries_results, backend=parameters["pandas_mode"], unit="s")
            queries_results["Backend"] = parameters["pandas_mode"]

        return {"ETL": [queries_results], "ML": []}
    except Exception:
        traceback.print_exc(file=sys.stdout)
        sys.exit(1)
