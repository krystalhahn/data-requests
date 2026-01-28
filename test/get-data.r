# source(here::here(".Rprofile"))

# Capture and parse arguments
args <- commandArgs(trailingOnly = TRUE)
output_file <- args[1]

df <- mtcars
write.csv(df, file = output_file, row.names = FALSE)
