# INPUT PARAMETERS
# _X_RAW_DB, _LO_LIMIT_1
# raw data in csv using db structure, i.e., a single row contains:
# code of representative, code of division, encoded vote (i.e. one of -1, 1, 0, NA)
# for example:
# “Joe Europe”,”Division-007”,”yes”


Xsource = read.csv("praha/data/votes.csv")

Xsource$vote_event_id = as.factor(Xsource$vote_event_id)
Xsource$voter_id = as.factor(Xsource$voter_id)
#Xsource = Xsource[c("voter_id","vote_event_id","option")]
Xsource$option_numeric = rep(0,length(Xsource$option))
Xsource$option_numeric[Xsource$option=='yes'] = 1
Xsource$option_numeric[Xsource$option=='no'] = -1
Xsource$option_numeric[Xsource$option=='abstain'] = -1
Xsource$option_numeric[Xsource$option=='not voting'] = NA
Xsource$option_numeric[Xsource$option=='absent'] = NA
Xsource$option_numeric = as.numeric(Xsource$option_numeric)

#Xrawdb = _X_RAW_DB
Xrawdb = Xsource
# lower limit to eliminate from calculations, e.g., .1; number
lo_limit = .1

# reorder data; divisions x persons
# we may need to install and/or load some additional libraries
# install.packages("reshape2")
library("reshape2")
# library("reshape2", lib.loc="/home/michal/R/x86_64-pc-linux-gnu-library/3.6")
# install.packages("sqldf")
# library("sqldf")

#prevent reordering, which is behaviour of acast:
#Xrawdb$V1 = factor(Xrawdb$V1, levels=unique(Xrawdb$V1))
Xrawdb$voter_id = factor(Xrawdb$voter_id, levels=unique(Xrawdb$voter_id))
Xraw = t(acast(Xrawdb,voter_id~vote_event_id,fun.aggregate=mean,value.var='option_numeric'))
Xpeople = dimnames(Xraw)[[2]]
Xvote_events = dimnames(Xraw)[[1]]
# Xraw=apply(Xraw,1,as.numeric)
mode(Xraw) = 'numeric'
# scale data; divisions x persons (mean=0 and sd=1 for each division)
Xstand=t(scale(t(Xraw),scale=TRUE))

# WEIGHTS
# weights 1 for divisions, based on number of persons in division
w1 = apply(abs(Xraw)==1,1,sum,na.rm=TRUE)/max(apply(abs(Xraw)==1,1,sum,na.rm=TRUE))
w1[is.na(w1)] = 0
# weights 2 for divisions, "100:100" vs. "195:5"
w2 = 1 - abs(apply(Xraw==1,1,sum,na.rm=TRUE) - apply(Xraw==-1,1,sum,na.rm=TRUE))/apply(!is.na(Xraw),1,sum)
w2[is.na(w2)] = 0

# analytical charts for weights:
#plot(w1)
#plot(w2)
#plot(w1*w2)

# weighted scaled matrix; divisions x persons
X = Xstand * w1 * w2

# MISSING DATA
# index of missing data; divisions x persons
I = X
I[!is.na(X)] = 1
I[is.na(X)] = 0

# weighted scaled with NA substituted by 0; division x persons
X0 = X
X0[is.na(X)]=0

# EXCLUSION OF REPRESENTATIVES WITH TOO FEW VOTES (WEIGHTED)
# weights for non missing data; division x persons
Iw = I*w1*w2
# sum of weights of divisions for each persons; vector of length “persons”
s = apply(Iw,2,sum)
pw = s/(t(w1)%*%w2)
# index of persons kept in calculation; vector of length “persons”
pI = pw > lo_limit
# weighted scaled with NA->0 and cutted persons with too few weighted votes; division x persons
X0c = X0[,pI]
# index of missing cutted (excluded) persons with too few weighted votes; divisions x persons
Ic = I[,pI]
# indexes of cutted (excluded) persons with too few votes; divisions x persons
Iwc = Iw[,pI]

# “X’X” MATRIX
# weighted X’X matrix with missing values substituted and excluded persons; persons x persons
C=t(X0c)%*%X0c * 1/(t(Iwc)%*%Iwc) * (sum(w1*w1*w2*w2))
# substitution of missing data in "covariance" matrix (the simple way)
C0 = C
C0[is.na(C)] = 0

# DECOMPOSITION
# eigendecomposition
Xe=eigen(C0)
# W (rotation values of persons)
W = Xe$vectors
# projected divisions into dimensions
Xy=X0c%*%W

# analytical charts of projection of divisions and lambdas
#plot(Xy[,1],Xy[,2])
#plot(sqrt(Xe$values[1:10]))

# lambda matrix
sigma = sqrt(Xe$values)
sigma[is.na(sigma)] = 0
lambda = diag(sigma)
# unit scaled lambda matrix
lambdau = sqrt(lambda^2/sum(lambda^2))

# projection of persons into dimensions
Xproj = W%*%lambda
# scaled projection of persons into dimensions
Xproju = W%*%lambdau*sqrt(dim(W)[1])

# analytical chart
# plot(Xproj[,1],Xproj[,2])
# plot(Xproju[,1],Xproju[,2])

# lambda^-1 matrix
lambda_1 = diag(sqrt(1/Xe$values))
lambda_1[is.na(lambda_1)] = 0

# Z (rotation values of divisions)
Z = X0c%*%W%*%lambda_1

# analytical charts
# second projection
Xproj2 = t(X0c) %*% Z
# without missing values, they are equal:
#plot(Xproj[,1],Xproj2[,1])
#plot(Xproj[,2],Xproj2[,2])

Xproj3u = W%*%lambdau * sqrt(lambda[1,1])
Xy3u=X0c%*%W / sqrt(lambda[1,1])

# "correlation matrix" (for charting)
invSC0 = solve(diag(sqrt(diag(C0))))
Corr0 = invSC0 %*% C0 %*% invSC0
rownames(Corr0) = rownames(C0)
colnames(Corr0) = colnames(C0)
# save into JSON file:
# setwd("home/michal/dev/wpca/psp/cs-2017-2019/")
# library("jsonlite", lib.loc="/home/michal/R/x86_64-pc-linux-gnu-library/3.4")
# sink(file="correlation_from_r.json")
# serializeJSON(as.data.frame(Corr0))
# sink()

# SAVE
write.csv(data.frame(data.frame(Xpeople, pI)[pI, ], Xproju[,1:3]), "Xproju.csv")
# write.csv(data.frame(Xpeople, pI)[pI, ], "Xpeople.csv")
