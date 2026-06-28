install.packages(c("dbplyr", "RSQLite"))
library(RSQLite)
library(dbplyr)

library(dplyr)
library(dbplyr)
install.packages("ggplot2")
library(ggplot2)

#% Source - https://stackoverflow.com/a/79008255
#% Posted by danieldavid521
#% Retrieved 2026-06-27, License - CC BY-SA 4.0

library(RSQLite)
filename <- "/Users/Alex/Downloads/Bureau/test/SecondTry/Code/GettingTrainingData/polymarket.db"
sqlite.driver <- dbDriver("SQLite")
db <- dbConnect(sqlite.driver,dbname = filename)
Tradesindb <- dbReadTable(db,"trades")
Marketsindb <- dbReadTable(db,"markets")
Usersindb <- dbReadTable(db,"users")
df <- merge(merge(Tradesindb,Marketsindb,by="conditionId"),Usersindb,by="wallet")
rm(Tradesindb)
rm(Marketsindb)
rm(Usersindb)
gc()

### NUMBER OF TRADES PER PRICE AND THE WINRATE FOR EACH BUCKET OF PRICE (0.01)
ggplot(subset(readindb, size > 5), aes(x = price, fill=factor(won))) + 
  geom_histogram(binwidth = 0.01, position="stack") + 
  labs(y = "Count", fill = "won")

### WINRATE FOR EACH BUCKET OF PRICE (0.01)
ggplot(subset(readindb, size > 5), aes(x = price, fill=factor(won))) +
  geom_histogram(binwidth = 0.01, position = "fill") +
  labs(y = "Proportion", fill = "won") + geom_abline(slope=1,intercept=0)
