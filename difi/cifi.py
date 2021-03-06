import time
import numpy as np
import pandas as pd

from .utils import _checkColumnTypes
from .utils import _classHandler
from .metrics import calcFindableMinObs
from .metrics import calcFindableNightlyLinkages


__all__ = ["analyzeObservations"]

def analyzeObservations(observations,
                        classes=None,
                        metric="min_obs",
                        column_mapping={
                            "linkage_id": "linkage_id",
                            "obs_id": "obs_id",
                            "truth": "truth"
                        },
                        **metric_kwargs):
    """
    Can I Find It?

    Analyzes a DataFrame containing observations. These observations need at least two columns:
    i) the observation ID column
    ii) the truth column
    
    Parameters
    ----------
    observations : `~pandas.DataFrame`
        Pandas DataFrame with at least two columns: observation IDs and the truth values
        (the object to which the observation belongs to).
    metric : {'min_obs', 'nightly_linkages', callable}
        The desired findability metric that calculates which truths are actually findable. 
        If 'min_obs' [default]:
            Finds all truths with a minimum of min_obs observations and the observations
            that makes them findable.
            See `~difi.calcFindableMinObs` for more details.
        If 'nightly_linkages':
            Finds the truths that have at least min_linkage_nights linkages of length
            linkage_min_obs or more. Observations are considered to be in a possible intra-night
            linkage if their observation time does not exceed max_obs_separation.
            See `~difi.calcFindableNightlyLinkages` for more details.
        If callable:
            A user-defined function call also be passed, this function must return a `~pandas.DataFrame` 
            with the truth IDs that are findable as an index, and a column named
            'obs_ids' containing `~numpy.ndarray`s of the observations that made each truth findable.
    classes : {dict, str, None}
        Analyze observations for truths grouped in different classes. 
        str : Name of the column in the dataframe which identifies 
            the class of each truth.
        dict : A dictionary with class names as keys and a list of unique 
            truths belonging to each class as values.
        None : If there are no classes of truths.
    column_mapping : dict, optional
        The mapping of columns in observations to internally used names. 
        Needs at least the following: "truth": ... and "obs_id" : ... . Other
        columns may be needed for different findability metrics.
    **metric_kwargs 
        Any additional keyword arguments are passed to the desired findability metric. 
        Note that column_mapping is also passed to the findability metric.
    
    Returns
    -------
    all_truths: `~pandas.DataFrame`
        A per-truth summary.
        
        Columns:
            "truth" : str
                Truth
            "num_obs" : int
                Number of observations in the observations dataframe
                for each truth
            "findable" : int
                1 if the object is findable, 0 if the object is not findable.
                (NaN if no findable column is found in the all_truths dataframe)

    findable_observations : `~pandas.DataFrame`
        A breakdown of the which observations made each object findable.
        Columns : 
            "obs_ids" : `~numpy.ndarray`
                Observation IDs that made each truth findable.

    summary : `~pandas.DataFrame`
        A per-class summary.
        
        Columns:
            "class" : str
                Name of class (if none are defined, will only contain) "All". 
            "num_members" : int
                Number of unique truths that belong to the class.
            "num_obs" : int
                Number of observations of truths belonging to the class in 
                the observations dataframe. 
            "findable" : int
                Number of truths deemed findable (all_truths must be passed to this 
                function with a findable column)
        
    Raises
    ------
    TypeError : If the truth column in observations does not have type "Object"
    """
    truth_col = column_mapping["truth"]

    # Raise error if there are no observations
    if len(observations) == 0: 
        raise ValueError("There are no observations in the observations DataFrame!")
        
    # Check column types
    _checkColumnTypes(observations, ["truth"], column_mapping)
    
    num_observations_list = []
    num_truths_list = []
    num_findable_list = []
        
    # Populate all_truths DataFrame
    dtypes = np.dtype([
        (truth_col, str),
        ("num_obs", int),
        ("findable", int)])
    data = np.empty(0, dtype=dtypes)
    all_truths = pd.DataFrame(data)
    
    num_obs_per_object = observations[truth_col].value_counts().values
    num_obs_descending = observations[truth_col].value_counts().index.values
    all_truths[truth_col] = num_obs_descending
    all_truths["num_obs"] = num_obs_per_object
    
    if metric == "min_obs":
        findable_observations = calcFindableMinObs(observations, column_mapping=column_mapping, **metric_kwargs)
    elif metric == "nightly_linkages":
        findable_observations = calcFindableNightlyLinkages(observations, column_mapping=column_mapping, **metric_kwargs)
    elif callable(metric):
        findable_observations = metric(observations, column_mapping=column_mapping, **metric_kwargs)
    else:
        err = (
            "\nmetric should be either 'min_obs', 'nightly_linkages', or a user-defined function that returns\n"
            "a `~pandas.DataFrame` with the truth IDs that are findable as an index, and a column named\n"
            "'obs_ids' containing `~numpy.ndarray`s of the observations that made each truth findable")
        raise ValueError(err)

    all_truths.loc[:, "findable"] = 0
    all_truths.loc[all_truths[truth_col].isin(findable_observations[truth_col].values), "findable"] = 1
        
    all_truths["findable"] = all_truths["findable"].astype(int)
    all_truths.sort_values(
        by=["num_obs", truth_col], 
        ascending=[False, True], 
        inplace=True
    )
    all_truths.reset_index(
        inplace=True, 
        drop=True
    )
    
    class_list, truths_list = _classHandler(classes, observations, column_mapping)

    for c, v in zip(class_list, truths_list):
        
        num_obs = len(observations[observations[truth_col].isin(v)])
        unique_truths = observations[observations[truth_col].isin(v)][truth_col].unique()
        num_unique_truths = len(unique_truths)
        findable = int(all_truths[all_truths[truth_col].isin(v)]["findable"].sum())
        
        num_observations_list.append(num_obs)
        num_truths_list.append(num_unique_truths)
        num_findable_list.append(findable)

    # Prepare summary DataFrame
    summary = pd.DataFrame({
        "class" : class_list,
        "num_members" : num_truths_list,
        "num_obs" : num_observations_list,
        "findable" : num_findable_list
    })
    summary.sort_values(by=["num_obs", "class"], ascending=False, inplace=True)
    summary.reset_index(inplace=True, drop=True)
    
    return all_truths, findable_observations, summary

