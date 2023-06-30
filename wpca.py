"""WPCA script in python."""

# Note: INPUT PARAMETERS
# _X_RAW_DB, _LO_LIMIT_1
# raw data in csv using db structure, i.e., a single row contains:
# code of representative, code of division, encoded vote (i.e. one of -1, 1, 0, NA)
# for example:
# “Joe Europe”,”Division-007”,”yes”

import pandas as pd
import numpy as np

localpath = "./"

# quick fix setting rotation
rotate = {
  'column': 'voter_id',
  'value': 6074,  # Petr Fiala
  'dims': [1, 1]
}

# quick settings for correct dates in charts
first_half_year = {"half": 2, "year": 2021}

Xsource = pd.read_csv(localpath + "data/votes.csv")

# recode options
conditions = [
  Xsource['option'].eq('yes'),
  Xsource['option'].isin(['no', 'abstain']),
  Xsource['option'].isin(['not voting', 'absent'])
]

nvalues = [1, -1, pd.NA]

Xsource['option_numeric'] = np.select(conditions, nvalues, default=pd.NA)

#Xrawdb = _X_RAW_DB
Xrawdb = Xsource

# lower limit to eliminate from calculations, e.g., .1; number
lo_limit = 0.1

Xraw = pd.pivot_table(Xrawdb, values='option_numeric', columns='voter_id', index='vote_event_id', aggfunc='first', fill_value=np.nan)

Xpeople = Xraw.columns
Xvote_events = Xraw.index

# Scale the data
Xstand = Xraw.sub(Xraw.mean(axis=1), axis=0).div(Xraw.std(axis=1, ddof=0), axis=0)

# WEIGHTS
# weights 1 for divisions, based on number of persons in division
w1 = (np.abs(Xraw) == 1).sum(axis=1, skipna=True) / (np.abs(Xraw) == 1).sum(axis=1, skipna=True).max()
w1[np.isnan(w1)] = 0

# weights 2 for divisions, "100:100" vs. "195:5"
w2 = 1 - np.abs((Xraw == 1).sum(axis=1, skipna=True) - (Xraw == -1).sum(axis=1, skipna=True)) / (~Xraw.isna()).sum(axis=1, skipna=True)
w2[np.isnan(w2)] = 0

# weighted scaled matrix; divisions x persons
X = Xstand.mul(w1, axis=0).mul(w2, axis=0)

# weighted scaled with NA substituted by 0; division x persons
X0 = X.fillna(0)

# filter people with too low attendance
w = (w1 * w2).sum()
pw = Xraw.notna().mul(w1, axis=0).mul(w2, axis=0).sum(axis=0) / w
selected_voters = pw[pw > lo_limit].index.tolist()
X0c = X0.loc[:, selected_voters]    # for direct use
X0c = X0    # for use with time intervals

# I matrix
I = X.notna().astype(int).loc[:, selected_voters]
Iw = I.fillna(0).mul(w1, axis=0).mul(w2, axis=0)

# “X’X” MATRIX
# weighted X’X matrix with missing values substituted and excluded persons; persons x persons
# C=t(X0c)%*%X0c * 1/(t(Iwc)%*%Iwc) * (sum(w1*w1*w2*w2))
C = (X0c.T.dot(X0c) * (1 / (Iw.T.dot(Iw))) * (w1 * w1 * w2 * w2).sum()).fillna(0)

# DECOMPOSITION
# eigendecomposition
eigvals, eigvecs = np.linalg.eig(C)
# sort the eigenvectors and eigenvalues
idx = eigvals.argsort()[::-1]
eigvals = eigvals[idx]
eigvecs = eigvecs[:, idx]

# projected divisions into dimensions
Xy = X0c.dot(eigvecs)

# lambda matrix
sigma = np.sqrt(eigvals)
sigma = np.nan_to_num(sigma, nan=0)
lmbda = np.diag(sigma)
# unit scaled lambda matrix
lambdau = np.sqrt(lmbda.dot(lmbda) / lmbda.dot(lmbda).sum())

# projection of persons into dimensions
Xproj = eigvecs.dot(lmbda)
# scaled projection of persons into dimensions
Xproju = eigvecs.dot(lambdau) * np.sqrt(len(eigvecs))
Xprojudf = pd.DataFrame(Xproju)
Xprojudf.index = selected_voters

# lambda^-1 matrix
lambda_1 = np.diag(np.sqrt(1 / eigvals))
lambda_1 = np.nan_to_num(lambda_1)

# Z (rotation values of divisions)
Z = X0c.dot(eigvecs).dot(lambda_1)

# second projection
Xproj2 = X0c.T.dot(Z)
# without missing values, they are equal:
# Xproj, Xproj2

# save Xproju
out = Xprojudf.iloc[:, range(0, 3)]
out.index = Xproj2.index
out.reset_index(inplace=True)
out.columns = ['voter_id', 'dim1', 'dim2', 'dim3']

# rotate
row = out.loc[out[rotate['column']] == rotate['value']]
# dims
for i in range(0, 2):
  if (rotate['dims'][i]) * row['dim' + str(i + 1)].values[0] < 0:
    out.loc[:, 'dim' + str(i + 1)] = out['dim' + str(i + 1)] * -1

out.to_csv(localpath + "data/wpca.csv", index=False)



# PROJECTIONS, TIME INTERVALS
# time intervals = half years
lo_limitT = 0.1
# Convert the 'date' column to datetime type
vote_events = pd.read_csv(localpath + "data/vote_events.csv")
vote_events['date'] = pd.to_datetime(vote_events['date'])

# Get the first and last dates in the data
first_date = vote_events['date'].min()
last_date = vote_events['date'].max()

# Create a list to store the new DataFrames
new_dfs = []

# Iterate over each half year period
current_date = first_date
while current_date <= last_date:
  # Calculate the start and end dates of the current half year period
  period_start = pd.Timestamp(current_date.year, 1 if current_date.month <= 6 else 7, 1)
  period_end = pd.Timestamp(current_date.year, 7 if current_date.month <= 6 else 12, 31)

  # Filter the DataFrame for rows within the current half year period
  filtered_df = vote_events.loc[:, ['vote_event_id', 'date']].copy()

  filtered_df['in_time_period'] = filtered_df['date'].between(period_start, period_end)

  # Create a new variable 'in_time_period' indicating whether the row is in the given half year
  # filtered_df['in_time_period'] = True

  # Append the filtered DataFrame to the list of new DataFrames
  new_dfs.append(filtered_df)

  # Move to the next half year period
  current_date = period_end + pd.DateOffset(days=1)

# Access each new DataFrame in the list

projections = []
for i, filtered_df in enumerate(new_dfs):

  # filtered_df['in_time_period'].to_csv(localpath + "data/wpca_test.csv", index=False)

  XrawTc = Xraw.loc[:, selected_voters]
  filtered_df.index = filtered_df['vote_event_id']
  XrawTc[~filtered_df['in_time_period']] = np.nan



  # Xstand = Xraw.sub(Xraw.mean(axis=1), axis=0).div(Xraw.std(axis=1, ddof=0), axis=0)
  # XTc = (XrawTc - attr(Xstand,"scaled:center"))/attr(Xstand,"scaled:scale")
  XTc = Xraw.sub(Xraw.mean(axis=1), axis=0).div(Xraw.std(axis=1, ddof=0), axis=0)
  XTc[[~filtered_df['in_time_period']]] = np.nan

  # Indices of NAs; division x person
  TIc = XTc
  TIc = TIc.where(TIc.isna(), 1)
  TIc = TIc.fillna(0)
  TIc[[~filtered_df['in_time_period']]] = 0


  # weights for non missing data; divisions x persons
  # TIcw = TIc * w1 * w2
  # X = Xstand.mul(w1, axis=0).mul(w2, axis=0)
  TIcw = TIc.mul(w1, axis=0).mul(w2, axis=0)
  # sum of weights of divisions for each persons
  s = TIcw.sum(axis=0)
  pTW = s / max(s)
  # index of persons in calculation
  pTI = pTW > lo_limitT


  selected_votersT = pTI[pTI].index.tolist()

  XTw0cc = XTc.mul(w1, axis=0).mul(w2, axis=0).loc[:, selected_votersT].fillna(0)

  aZ = abs(Z)

  # dweights = t(t(aZ)%*%TIcc / apply(aZ,2,sum))      
  # dweights[is.na(dweights)] = 0

  TIcc = TIc.loc[:, selected_votersT]
  aZ_transpose = aZ.T

  column_sums = aZ.sum(axis=0)

  division_result = aZ_transpose / column_sums

  dweights = (aZ_transpose.dot(TIcc).T).div(column_sums).fillna(0)

  # XTw0ccproj = t(XTw0cc)%*%Z / dweights
  XTw0ccproj = XTw0cc.T.dot(Z).div(dweights)

  projections.append(XTw0ccproj)


# quick save to proper format
wpca1 = pd.read_csv(localpath + "data/wpca.v1.all.csv")

out = pd.DataFrame(columns=(wpca1.columns.tolist() + ['datum']))

for i, projection in enumerate(projections):
  p = projection.iloc[:, 0:3]
  p.columns = ['dim1', 'dim2', 'dim3']
  p.reset_index(inplace=True)
  p = p.merge(wpca1.loc[:, ['voter_id', 'příjmení', 'jméno', 'kandidátka', 'klub']], on='voter_id', how='left')
  p['datum'] = i

  out = pd.concat([out, p], axis=0)

# add no club
out['klub'] = out['klub'].fillna('Nezařazení')

# correct datum
def get_text(input_value):
  period_tf = {True: first_half_year['half'], False: 2 - ((first_half_year['half'] + 1) % 2)}
  year = first_half_year["year"] + (input_value + first_half_year["half"] - 1) // 2
  period = period_tf[(input_value % 2) == 0]
  return f"{period}. pol. {year}"

out['datum'] = out['datum'].apply(get_text)

# rotate
row = out.loc[out[rotate['column']] == rotate['value']]
# dims
for i in range(0, 2):
  if (rotate['dims'][i]) * row['dim' + str(i + 1)].values[0] < 0:
    out.loc[:, 'dim' + str(i + 1)] = out['dim' + str(i + 1)] * -1

out.to_csv(localpath + "data/wpca.halfyear.v1.csv", index=False)