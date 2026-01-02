library(readr)
library(dplyr)
library(tidyverse)

# get creators of GUID target objects ----
# in specified months

## August and September ----
# 814447 file GUIDs created
target_creators_89 <- read_csv("~/Desktop/target_creators_89.csv")
# 58138

summary(target_creators_89$file_count)
# Min. 1st Qu.  Median    Mean 3rd Qu.    Max. 
# 1.00    1.00    2.00   12.63    7.00 2632.00 

## July and June ----
# 119075 file GUIDs created
target_creators_67 <- read_csv("~/Desktop/target_creators_67.csv")
# 31620

summary(target_creators_67$file_count)
# Min.  1st Qu.   Median     Mean  3rd Qu.     Max. 
# 1.000    1.000    2.000    3.223    3.000 1419.000

# get creators of latest file version ----
## August and September ----
latest_version_creators_89 <- read_csv("~/Desktop/latest_version_creators_with_versions_89.csv")
# 54909

summary(latest_version_creators_89$file_count)
# Min. 1st Qu.  Median    Mean 3rd Qu.    Max. 
# 1.00    1.00    2.00   12.28    7.00 3317.00 

## June and July ----
latest_version_creators_67 <- read_csv("~/Desktop/latest_version_creators_with_versions_67.csv")
# 28486

summary(latest_version_creators_67$file_count)
# Min. 1st Qu.  Median    Mean 3rd Qu.    Max. 
# 1.000   1.000   1.000   2.961   3.000 636.000

# get creators of file version when GUID was minted ----
## June and July ----
minted_version_creators_67 <- read_csv("~/Desktop/creators_at_guid_version_67.csv")
# 28479

summary(minted_version_creators_67$file_count)
# Min. 1st Qu.  Median    Mean 3rd Qu.    Max. 
# 1.000   1.000   1.000   2.962   3.000 636.000

view(version_creators_67 %>% filter(!creator_guid %in% minted_version_creators_67$creator_guid))

## August and September ----
minted_version_creators_89 <- read_csv("~/Desktop/creators_at_guid_version_89.csv")
# 54909

summary(minted_version_creators_89$file_count)
# Min. 1st Qu.  Median    Mean 3rd Qu.    Max. 
# 1.00    1.00    2.00   12.28    7.00 3317.00 
# this is the exact same as the creators of the latest version
# however, there are slightly different numbers of creators
view(version_creators_89 %>% filter(!creator_guid %in% minted_version_creators_89$creator_guid))
# shows cases in which the creator of the latest version is different from the creator of the version at GUID minting

### validate latest_version_creators ----
rebuilt_latest_version_creators_89 <- file_info_89 %>%
  group_by(latest_version_creator) %>%
  summarize(file_count = n())
# 54854: 55 less rows than in creator level (54909)

view(latest_version_creators_89 %>% filter(!creator_guid %in% rebuilt_latest_version_creators_89$latest_version_creator))
# 58 creators in creator level that aren't in the file level

# do the common rows match?
compare_dfs(rebuilt_latest_version_creators_89 %>% 
              filter(latest_version_creator %in% latest_version_creators_89$creator_guid),
            latest_version_creators_89 %>%
              filter(creator_guid %in% rebuilt_latest_version_creators_89$latest_version_creator) %>%
              select(creator_guid, file_count) %>%
              rename(latest_version_creator = creator_guid),
            "latest_version_creator")
# appears to not match
comp <- rebuilt_latest_version_creators_89 %>% 
  rename(rebuilt_file_count = file_count) %>%
  left_join(latest_version_creators_89 %>%
              select(creator_guid, file_count),
            by = c("latest_version_creator" = "creator_guid")) %>%
  mutate(diff = file_count - rebuilt_file_count)

### validate minted_version_creators ----
rebuilt_minted_version_creators_89 <- file_info_89 %>%
  group_by(minted_version_creator) %>%
  summarize(file_count = n())
# 54851: 58 less rows than in creator level (54909)

# do the common rows match?
compare_dfs(rebuilt_minted_version_creators_89 %>% 
              filter(minted_version_creator %in% minted_version_creators_89$creator_guid),
            minted_version_creators_89 %>%
              filter(creator_guid %in% rebuilt_minted_version_creators_89$minted_version_creator) %>%
              select(creator_guid, file_count) %>%
              rename(minted_version_creator = creator_guid),
            "minted_version_creator")
# appears to not match

### validate target_creators ----
rebuilt_target_creators_89 <- file_info_89 %>%
  group_by(target_creator) %>%
  summarize(file_count = n())
# 58138: same number of rows as in creator level

compare_dfs(rebuilt_target_creators_89,
            target_creators_89 %>%
              select(creator_guid, file_count) %>%
              rename(target_creator = creator_guid),
            "target_creator")
# compare_dfs() confirms same data as in creator level

# inspect empty GUIDs and overlapping target objects ----
check_dups <- function(path, empty_only = FALSE) {
  
  full_df <- read_csv(path, show_col_types = FALSE)
  
  total_rows <- nrow(full_df)
  total_targets <- n_distinct(full_df$target_guid)
  
  empty_rows <- NULL
  empty_targets <- NULL
  
  # restrict universe if requested
  if (empty_only) {
    df <- full_df %>% filter(is.na(name))
    empty_rows <- nrow(df)
    empty_targets <- n_distinct(df$target_guid)
  } else {
    df <- full_df
  }
  
  # overlaps are computed ONLY within df
  overlaps <- df %>%
    group_by(target_guid) %>%
    filter(n() > 1) %>%
    ungroup()
  
  list(
    total_rows = total_rows,
    total_targets = total_targets,
    empty_rows = empty_rows,
    empty_targets = empty_targets,
    overlap_rows = nrow(overlaps),
    overlap_targets = n_distinct(overlaps$target_guid),
    data = overlaps
  )
}

## June ----
file_info_6 <- check_dups("~/Desktop/file_guids_6.csv", empty_only = TRUE)

file_info_6$total_rows
# 56578 total file GUIDs created in June

file_info_6$empty_rows
# 9811 of those were empty (empty name, etc.)

file_info_6$overlap_rows
## 5915 of those empty GUIDs had the same target object

file_info_6$overlap_targets
### 1262 unique target objects among the overlapping empty GUIDs

## July ----
file_info_7 <- check_dups("~/Desktop/file_guids_7.csv", empty_only = TRUE)
# 62514 total file GUIDs created in July
# 7858 of those were empty
## 4059 of those empty GUIDs had the same target object
### 1224 unique target objects among the overlapping empty GUIDs

## August ----
file_info_8 <- check_dups("~/Desktop/file_guids_8.csv", empty_only = TRUE)
# 299412 total file GUIDs created in August
# 22349 of those were empty
## 12705 of those empty GUIDs had the same target object
### 3772 unique target objects among the overlapping empty GUIDs
