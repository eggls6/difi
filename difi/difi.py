import numpy as np
import pandas as pd

__all__ = ["analyzeLinkages"]

def analyzeLinkages(observations, 
                    linkageMembers, 
                    allLinkages=None, 
                    allTruths=None,
                    minObs=5, 
                    contaminationThreshold=0.2, 
                    columnMapping={"linkage_id": "linkage_id",
                                   "obs_id": "obs_id",
                                   "truth": "truth"}):
    """
    Did I Find It? 
    
    Parameters
    ----------
    observations : `~pandas.DataFrame`
        Pandas DataFrame with at least two columns: observation IDs and the truth values
        (the object to which the observation belongs to).
    linkageMembers : `~pandas.DataFrame`
        Pandas DataFrame with at least two columns: linkage IDs and the observation 
    allLinkages : {`~pandas.DataFrame`, None}, optional
        Pandas DataFrame with one row per linkage with at least one column: linkage IDs.
        If None, allLinkages will be created.
        [Default = None]
    allTruths : {`~pandas.DataFrame`, None}, optional
        Pandas DataFrame with one row per unique truth with at least one column: truths.
        If None, allTruths will be created.
        [Default = None]
    minObs : int, optional
        The minimum number of observations belonging to one object for a linkage to be pure. 
        The minimum number of observations belonging to one object in a contaminated linkage
        (number of contaminated observations allowed is set by the contaminationThreshold)
        for the linkage to be partial. For example, if minObs is 5 then any linkage with 5 or more 
        detections belonging to a unique object, with no detections belonging to any other object will be 
        considered a pure linkage and the object is found. Likewise, if minObs is 5 and contaminationThreshold is 
        0.2 then a linkage with 10 members, where 8 belong to one object and 2 belong to other objects, will 
        be considered a partial linkage, and the object with 8 detections is considered found. 
        [Default = 5]
    contaminationThreshold : float, optional 
        Number of detections expressed as a percentage belonging to other objects in a linkage
        allowed for the object with the most detections in the linkage to be considered found. 
        [Default = 0.2]
    columnMapping : dict, optional
        The mapping of columns in observations and linkageMembers to internally used names. 
        Needs the following: "linkage_id" : ..., "truth": ... and "obs_id" : ... .
        
    Returns
    -------
    allLinkages : `~pandas.DataFrame`
        DataFrame with added pure, partial, false, contamination, num_obs, num_members, linked_truth 
    allTruths : `~pandas.DataFrame`
        DataFrame with added found_pure, found_partial, found columns. 
    """
    # If allLinkages DataFrame does not exist, create it
    if allLinkages == None:
        linkage_ids = linkageMembers[columnMapping["linkage_id"]].unique()
        linkage_ids.sort()
        allLinkages = pd.DataFrame({
            columnMapping["linkage_id"] : linkage_ids})
    
    # Prepare allLinkage columns
    allLinkages["num_members"] = np.ones(len(allLinkages)) * np.NaN
    allLinkages["num_obs"] = np.ones(len(allLinkages)) * np.NaN
    allLinkages["pure"] = np.zeros(len(allLinkages), dtype=int)
    allLinkages["partial"] = np.zeros(len(allLinkages), dtype=int)
    allLinkages["false"] = np.zeros(len(allLinkages), dtype=int)
    allLinkages["contamination"] = np.ones(len(allLinkages), dtype=int) * np.NaN
    allLinkages["linked_truth"] = np.ones(len(allLinkages), dtype=int) * np.NaN
    
    # Add the number of observations each linkage as 
    allLinkages["num_obs"] = linkageMembers["linkage_id"].value_counts().sort_index().values

    # If allTruths DataFrame does not exist, create it
    if allTruths == None:
        truths = observations[columnMapping["truth"]].unique()
        allTruths = pd.DataFrame({
            columnMapping["truth"] : truths,
            "found_pure" : np.zeros(len(truths), dtype=int),
            "found_partial" : np.zeros(len(truths), dtype=int),
            "found" : np.zeros(len(truths), dtype=int)})
        
    ### Calculate the number of unique truth's per linkage
    
    # Grab only observation IDs and truth from observations
    linkage_truth = observations[[columnMapping["obs_id"], columnMapping["truth"]]]
    
    # Merge truth from observations with linkageMembers on observation IDs
    linkage_truth = linkage_truth.merge(
        linkageMembers[[columnMapping["linkage_id"],
                        columnMapping["obs_id"]]], 
        on=columnMapping["obs_id"])
    
    # Drop observation ID column
    linkage_truth.drop(columns="obs_id", inplace=True)
    
    # Drop duplicate rows, any correct linkage will now only have one row since
    # all the truth values would have been the same, any incorrect linkage
    # will now have multiple rows for each unique truth value
    linkage_truth.drop_duplicates(inplace=True)
    
    # Sort by linkage IDs and reset index
    linkage_truth.sort_values(by=columnMapping["linkage_id"], inplace=True)
    linkage_truth.reset_index(inplace=True, drop=True)
    
    # Grab the number of unique truths per linkage and update 
    # the allLinkages DataFrame with the result
    unique_truths_per_linkage = linkage_truth[columnMapping["linkage_id"]].value_counts()
    allLinkages["num_members"] = unique_truths_per_linkage.sort_index().values
    
    ### Find all the pure linkages and identify them as such
    
    # All the linkages where num_members = 1 are pure linkages
    single_member_linkages = linkage_truth[
        linkage_truth[columnMapping["linkage_id"]].isin(
            allLinkages[(allLinkages["num_members"] == 1) & (allLinkages["num_obs"] >= minObs)][columnMapping["linkage_id"]])]
    
    # Update the linked_truth field in allLinkages with the linked object
    pure_linkages = allLinkages[columnMapping["linkage_id"]].isin(single_member_linkages[columnMapping["linkage_id"]])
    allLinkages.loc[pure_linkages, "linked_truth"] = single_member_linkages[columnMapping["truth"]].values
    
    # Update the pure field in allLinkages to indicate which linkages are pure
    allLinkages.loc[(allLinkages["linked_truth"].notna()), "pure"] = 1
    
    ### Find all the partial linkages and identify them as such
    
    # Grab only observation IDs and truth from observations
    linkage_truth = observations[[columnMapping["obs_id"], columnMapping["truth"]]]

    # Merge truth from observations with linkageMembers on observation IDs
    linkage_truth = linkage_truth.merge(
        linkageMembers[[columnMapping["linkage_id"],
                        columnMapping["obs_id"]]], 
        on=columnMapping["obs_id"])

    # Remove non-pure linkages
    linkage_truth = linkage_truth[linkage_truth[columnMapping["linkage_id"]].isin(
        allLinkages[allLinkages["pure"] != 1][columnMapping["linkage_id"]])]

    # Drop observation ID column
    linkage_truth.drop(columns="obs_id", inplace=True)

    # Group by linkage IDs and truths, creates a multi-level index with linkage ID
    # as the first index, then truth as the second index and as values is the count 
    # of the number of times the truth shows up in the linkage
    linkage_truth = linkage_truth.groupby(linkage_truth[[
        columnMapping["linkage_id"],
        columnMapping["truth"]]].columns.tolist(), as_index=False).size()

    # Reset the index to create a DataFrame
    linkage_truth = linkage_truth.reset_index()

    # Rename 0 column to num_obs which counts the number of observations
    # each unique truth has in each linkage
    linkage_truth.rename(columns={0: "num_obs"}, inplace=True)

    # Sort by linkage ID and num_obs so that the truth with the most observations
    # in each linkage is last for each linkage
    linkage_truth.sort_values(by=[columnMapping["linkage_id"], "num_obs"], inplace=True)

    # Drop duplicate rows, keeping only the last row 
    linkage_truth.drop_duplicates(subset=[columnMapping["linkage_id"]], inplace=True, keep="last")

    # Grab all linkages and merge truth from observations with linkageMembers on observation IDs
    linkage_truth = linkage_truth.merge(allLinkages[[columnMapping["linkage_id"], "num_obs"]], on=columnMapping["linkage_id"])

    # Rename num_obs column in allLinkages to total_num_obs
    linkage_truth.rename(columns={"num_obs_x": "num_obs", "num_obs_y": "total_num_obs"}, inplace=True)

    # Calculate contamination 
    linkage_truth["contamination"] = (1 - linkage_truth["num_obs"] / linkage_truth["total_num_obs"])
    
    # Select partial linkages: have at least the minimum observations of a single truth and have no
    # more than x% contamination
    partial_linkages = linkage_truth[(linkage_truth["num_obs"] >= minObs) 
                                   & (linkage_truth["contamination"] <= contaminationThreshold)]
    
    # Update allLinkages to indicate partial linkages, update linked_truth field
    # Set every linkage that isn't partial or pure to false
    allLinkages.loc[allLinkages[columnMapping["linkage_id"]].isin(partial_linkages[columnMapping["linkage_id"]]), "linked_truth"] = partial_linkages[columnMapping["truth"]].values
    allLinkages.loc[allLinkages[columnMapping["linkage_id"]].isin(partial_linkages[columnMapping["linkage_id"]]), "partial"] = 1
    allLinkages.loc[allLinkages[columnMapping["linkage_id"]].isin(partial_linkages[columnMapping["linkage_id"]]), "contamination"] = partial_linkages["contamination"].values
    allLinkages.loc[(allLinkages["pure"] != 1) & (allLinkages["partial"] != 1), "false"] = 1

    # Update allTruths to indicate which objects were found in pure and partial clusters, if found in either the object is found
    allTruths.loc[allTruths[columnMapping["truth"]].isin(allLinkages[allLinkages["pure"] == 1]["linked_truth"].values), "found_pure"] = 1
    allTruths.loc[allTruths[columnMapping["truth"]].isin(allLinkages[allLinkages["partial"] == 1]["linked_truth"].values), "found_partial"] = 1
    allTruths.loc[(allTruths["found_pure"] == 1) | (allTruths["found_partial"] == 1), "found"] = 1
    
    return allLinkages, allTruths