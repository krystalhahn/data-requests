library(readr)
library(tidyverse)
library(dplyr)
library(stringr)
library(googlesheets4)
library(tibble)
library(purrr)
library(tidyr)
gs4_auth(email = "krystal@cos.io", cache = FALSE)

# starts with the osf_participants df from trainings_data_prep.R:
# training participants who were matched to OSF accounts

# age at time of training ----

participant_ages <- osf_participants %>%
  mutate(age_at_first_training = as.numeric(difftime(first_training_date, u.date_confirmed, unit = "days")))

summary(participant_ages$age_at_first_training)

summary_ages <- participant_ages %>%
  select(age_at_first_training) %>%
  summarise(
    mean = mean(age_at_first_training, na.rm = TRUE),
    median = median(age_at_first_training, na.rm = TRUE),
    min = min(age_at_first_training, na.rm = TRUE),
    max = max(age_at_first_training, na.rm = TRUE), 
    sd = sd(age_at_first_training, na.rm = TRUE),
    Q1 = quantile(age_at_first_training, 0.25, na.rm = TRUE),
    Q3 = quantile(age_at_first_training, 0.75, na.rm = TRUE),
    n = n()
  )
# there are some negative ages = accounts confirmed after training
# 5 NAs because they are inactive

ggplot(participant_ages, aes(x = age_at_first_training/365)) +
  geom_density() +
  geom_vline(xintercept = summary_ages$mean/365, linetype = "dashed", color = "red") +
  labs(
    x = "Age at first training (in years)",
    title = "Age of OSF account relative to training"
  ) +
  theme_minimal() +
  theme(
    legend.position = "top",
    plot.title = element_text(face = "bold")
  )

# segment participants into LOS metrics ----

# LOS data for all users
# for now, up to September 2025 LOS
los_users <- read_csv("~/Desktop/script_outputs/nps_users_final/nps_users_2025-10-06.csv") %>%
  subset(u.date_confirmed < "2025-10-01") %>%
  # 916849 users
  rowwise() %>%
  mutate(los_project = ifelse(public_projects_created > 0, T, F),
         los_registration = ifelse(public_registrations_created > 0 | embargoed_registrations_created > 0, T, F),
         los_preprint = ifelse(published_preprints_created > 0, T, F)) %>%
  mutate(
    user_type = case_when(
      sum(los_project, los_registration, los_preprint) == 3 ~ "champion",
      sum(los_project, los_registration, los_preprint) == 2 ~ "active",
      sum(los_project, los_registration, los_preprint) == 1 ~ "emerging",
      TRUE ~ "novice"
    ),
    is_institutional = !is.na(institutions) & institutions != ""
  )

# LOS data for matched participants
los_participants <- osf_participants %>%
  left_join(los_users %>% select(-u.username, -u.date_confirmed), by = 'u._id')

# LOS distribution among matched participants
table(los_participants$user_type)
# active champion emerging   novice 
# 10       5       32      118 

los_inst_table <- los_participants %>%
  group_by(inst, user_type) %>%
  summarize(n = n(), .groups = "drop") %>%
  pivot_wider(
    names_from = user_type,
    values_from = n,
    values_fill = 0,
    names_glue = "{user_type}_n"
  ) %>%
  select(inst, novice_n, emerging_n, active_n, champion_n, NA_n)

los_inst_prop <- los_inst_table %>%
  rowwise() %>%
  mutate(
    total = sum(c_across(novice_n:NA_n)),  # sum across user types
    novice_prop   = novice_n / total,
    emerging_prop = emerging_n / total,
    active_prop   = active_n / total,
    champion_prop = champion_n / total,
    NA_prop = NA_n / total,
  ) %>%
  ungroup() %>%
  mutate(across(where(is.numeric), ~ round(.x*100))) %>%
  select(inst, ends_with("_prop"))

# difference in counts of nodes/reg/preprints (NPS) ----

# until August 2025
nps_0925 <- osf_participants %>%
  left_join(read_csv("~/Desktop/script_outputs/nps_users_final/nps_users_2025-09-04.csv") %>%
              subset(u.date_confirmed < "2025-09-01") %>%
              rowwise() %>%
              select(-u.username, -u.date_confirmed),
            by = "u._id")

# leave LOS type numeric but number from 1-4 to calculate differences
# leave user_type NA if no NPS data (confirmed after 9/1 or inactive, etc.)
los_0925 <- nps_0925 %>%
  rowwise() %>%
  mutate(los_project = ifelse(public_projects_created > 0, T, F),
         los_registration = ifelse(public_registrations_created > 0 | embargoed_registrations_created > 0, T, F),
         los_preprint = ifelse(published_preprints_created > 0, T, F)) %>%
  mutate(
    user_type = case_when(
      is.na(public_projects_created) & is.na(public_registrations_created) & is.na(embargoed_registrations_created) & is.na(published_preprints_created) ~ NA_real_,
      sum(los_project, los_registration, los_preprint) == 3 ~ 4,
      sum(los_project, los_registration, los_preprint) == 2 ~ 3,
      sum(los_project, los_registration, los_preprint) == 1 ~ 2,
      TRUE ~ 1
    ),
    is_institutional = !is.na(institutions) & institutions != ""
  ) %>%
  select(Email, u._id, u.username, orcid, where(is.numeric))

# end of 2024
nps_0125 <- osf_participants %>%
  left_join(read_csv("~/Desktop/script_outputs/nps_users_final/nps_users_2025-01-02.csv") %>%
              subset(u.date_confirmed < "2025-01-01") %>%
              rowwise() %>%
              select(-u.username, -u.date_confirmed),
            by = "u._id")

los_0125 <- nps_0125 %>%
  rowwise() %>%
  mutate(los_project = ifelse(public_projects_created > 0, T, F),
         los_registration = ifelse(public_registrations_created > 0 | embargoed_registrations_created > 0, T, F),
         los_preprint = ifelse(published_preprints_created > 0, T, F)) %>%
  mutate(
    user_type = case_when(
      is.na(public_projects_created) & is.na(public_registrations_created) & is.na(embargoed_registrations_created) & is.na(published_preprints_created) ~ NA_real_,
      sum(los_project, los_registration, los_preprint) == 3 ~ 4,
      sum(los_project, los_registration, los_preprint) == 2 ~ 3,
      sum(los_project, los_registration, los_preprint) == 1 ~ 2,
      TRUE ~ 1
    ),
    is_institutional = !is.na(institutions) & institutions != ""
  ) %>%
  select(Email, u._id, u.username, orcid, where(is.numeric))

comp_npslos <- los_0925 %>%
  left_join(
    los_0125,
    by = "Email",
    suffix = c("_0925", "_0125")  # suffixes to distinguish columns
  )

# Identify numeric columns from the original los_0925 dataset
num_cols <- names(los_0925)[sapply(los_0925, is.numeric) & names(los_0925) != "Email"]

# Loop over numeric columns and compute diff = 0925 - 0125
for (col in num_cols) {
  comp_npslos[[paste0(col, "_diff")]] <- comp_npslos[[paste0(col, "_0925")]] -
    comp_npslos[[paste0(col, "_0125")]]
}

# Keep Email, _diff columns, and/or other columns as needed
comp_npslos <- comp_npslos %>%
  select(Email, ends_with("_diff"), everything())

summary_npslos <- comp_npslos %>%
  ungroup() %>%
  # filter(!is.na(public_projects_created_diff)) %>%
  # filter(if_all(ends_with("_diff"), ~ !is.na(.x))) %>%
  summarise(
    across(
      ends_with("_diff"),
      list(
        mean   = ~ round(mean(.x, na.rm = TRUE), 2),
        median = ~ median(.x, na.rm = TRUE),
        min    = ~ min(.x, na.rm = TRUE),
        max    = ~ max(.x, na.rm = TRUE),
        sd     = ~ round(sd(.x, na.rm = TRUE), 2),
        n      = ~ sum(!is.na(.x))
      )
    )
  ) %>%
  pivot_longer(
    cols = everything(),
    names_to = c("metric", "stat"),
    names_sep = "_diff_",
    values_to = "value"
  ) %>%
  pivot_wider(
    names_from = stat,
    values_from = value
  )

# (nps_data_prep.R) incorporate all of NPS/LOS data for other months ----
# to calculate change based on training_date
# taking los_list with compiled NPS/LOS data from nps_data_prep.R

# create a single dataframe
# get month before and after *last* training to calculate differences
los_long <- bind_rows(
  los_list,
  .id = "month_label"
) %>%
  mutate(
    month_label = str_remove(month_label, "^los_")
  ) %>%
  left_join(osf_participants %>% select(u._id, first_training_date, last_training_date, postsurvey_date, u.date_confirmed), by = "u._id") %>%
  mutate(month_before = format(first_training_date %m-% months(1), "%m%y"),
         month_of = format(first_training_date, "%m%y"),
         month_after = format(first_training_date %m+% months(1), "%m%y"),
         month_2_after = format(first_training_date %m+% months(2), "%m%y"),
         month_3_after 
         = format(first_training_date %m+% months(3), "%m%y"))

write_sheet(los_long %>% arrange(u._id), trainings_url, sheet = "longitudinal_npslos")

# Base numeric columns (columns you want to compute diffs for)
numeric_cols <- names(los_long)[sapply(los_long, is.numeric)]

# define before and after datasets
los_before <- los_long %>%
  filter(month_label == month_before) %>%
  select(u._id, all_of(numeric_cols)) %>%
  rename_with(~ paste0(.x, "_before"), numeric_cols)

los_of <- los_long %>%
  filter(month_label == month_of) %>%
  select(u._id, all_of(numeric_cols)) %>%
  rename_with(~ paste0(.x, "_of"), numeric_cols)

# less than 171 rows: 158 rows due to no 1025 data
los_after <- los_long %>%
  filter(month_label == month_after) %>%
  select(u._id, all_of(numeric_cols)) %>%
  rename_with(~ paste0(.x, "_after"), numeric_cols)

los_2_after <- los_long %>%
  filter(month_label == month_2_after) %>%
  select(u._id, all_of(numeric_cols)) %>%
  rename_with(~ paste0(.x, "_2_after"), numeric_cols)

los_3_after <- los_long %>%
  filter(month_label == month_3_after) %>%
  select(u._id, all_of(numeric_cols)) %>%
  rename_with(~ paste0(.x, "_3_after"), numeric_cols)

# function to compute differences and summary stats
summarize_los_diff <- function(los_before, los_after, suffix_before, suffix_after) {
  
  # # doesn't pass the los_before and los_after arguments as it should
  # suffix_before <- sub("^.*(_.*)$", "\\1", deparse(substitute(los_before)))
  # suffix_after <- sub("^.*(_.*)$", "\\1", deparse(substitute(los_after)))
  
  los_longdiff <- los_before %>%
    inner_join(los_after, by = "u._id", suffix = c(suffix_before, suffix_after))
  
  for (col in numeric_cols) {
    los_longdiff[[paste0(col, "_diff")]] <- los_longdiff[[paste0(col, suffix_after)]] -
      los_longdiff[[paste0(col, suffix_before)]]
  }
  
  los_diff <- los_longdiff %>%
    select(u._id, ends_with("_diff")) %>%
    distinct()
  
  summary_los <- los_diff %>%
    ungroup() %>%
    summarise(
      across(
        ends_with("_diff"),
        list(
          mean   = ~ round(mean(.x, na.rm = TRUE), 2),
          median = ~ median(.x, na.rm = TRUE),
          min    = ~ min(.x, na.rm = TRUE),
          max    = ~ max(.x, na.rm = TRUE),
          sd     = ~ round(sd(.x, na.rm = TRUE), 2),
          n      = ~ sum(!is.na(.x))
        )
      )
    ) %>%
    pivot_longer(
      cols = everything(),
      names_to = c("metric", "stat"),
      names_sep = "_diff_",
      values_to = "value"
    ) %>%
    pivot_wider(
      names_from = stat,
      values_from = value
    )
  
  return(summary_los)
}

## descriptives ----

# month before - month after training (2 month period)
summary_los <- summarize_los_diff(los_before, los_after, "_before", "_after")

# month before - 2 months after training (3 month period)
summary_los_2 <- summarize_los_diff(los_before, los_2_after, "_before", "_2_after")

# month before - 3 months after training (4 month period)
summary_los_3 <- summarize_los_diff(los_before, los_3_after, "_before", "_3_after")

# month before - month of (1 month period)
summary_los_of <- summarize_los_diff(los_before, los_of, "_before", "_of")
# way too tight because training could've happened right at the end of the month

# (when anchoring on first training) n counts are different (not 158) because:
# 85 _created n: 73 no before or after month (confirmed during month_after so no month_before data, no 10/25 data yet)
# 57 _contributor n: 101 before contributor columns added, no before or after month

# (when anchoring on last training) n counts are different (not 171) because:
# 117 _created n: no before or after month (confirmed during month_after so no month_before data, no 10/25 data yet)
# 75 _contributor n: before contributor columns added, no before or after month

# plot before and after NPS/LOS
los_longplot <- bind_rows(
  los_before %>% rename_with(~ str_remove(.x, "_before$")) %>% mutate(period = "before"),
  los_after  %>% rename_with(~ str_remove(.x, "_after$")) %>% mutate(period = "after")
) %>%
  pivot_longer(
    cols = -c(u._id, period),
    names_to = "metric",
    values_to = "value"
  ) %>%
  mutate(period = factor(period, levels = c("before", "after")))

## not just month before-month after: 5 month period ----
mlos_longplot <- bind_rows(
  los_before %>% rename_with(~ str_remove(.x, "_before$")) %>% mutate(month = "month before"),
  los_of %>% rename_with(~ str_remove(.x, "_of$")) %>% mutate(month = "month of"),
  los_after  %>% rename_with(~ str_remove(.x, "_after$")) %>% mutate(month = "month after"),
  los_2_after  %>% rename_with(~ str_remove(.x, "_2_after$")) %>% mutate(month = "2 months after"),
  los_3_after  %>% rename_with(~ str_remove(.x, "_3_after$")) %>% mutate(month = "3 months after")
) %>%
  pivot_longer(
    cols = -c(u._id, month),
    names_to = "metric",
    values_to = "value"
  ) %>%
  mutate(month = factor(month, levels = c("month before", "month of", "month after", "2 months after", "3 months after")))

# average metrics over five month period
mlos_longplot %>%
  group_by(month, metric) %>%
  summarise(mean_value = mean(value, na.rm = TRUE), .groups = "drop") %>%
  ggplot(aes(x = metric, y = mean_value, fill = month)) +
  geom_col(position = position_dodge()) +
  labs(
    title = "Before vs After Training — Average Metrics",
    x = "Metric",
    y = "Mean Value"
  ) +
  theme_minimal() +
  theme(axis.text.x = element_text(angle = 45, hjust = 1))

# change in metrics over the five month period
mlos_longplot %>%
  group_by(month, metric) %>%
  summarise(
    mean_value = mean(value, na.rm = TRUE),
    sd_value = sd(value, na.rm = TRUE),
    n = sum(!is.na(value)),
    se_value = sd_value / sqrt(n),
    .groups = "drop"
  ) %>%
  ggplot(aes(x = month, y = mean_value, group = metric, color = metric)) +
  geom_line(linewidth = 1) +
  geom_point(size = 2) +
  geom_errorbar(aes(ymin = mean_value - se_value, ymax = mean_value + se_value), width = 0.1, alpha = 0.5) +
  geom_vline(
    xintercept = which(levels(mlos_longplot$month) == "month of"),
    color = "red",
    linetype = "dashed",
    linewidth = 0.3
  ) +
  labs(
    title = "Change in Metrics Over Five Months",
    x = "Month Relative to Training",
    y = "Mean Value"
  ) +
  theme_minimal() +
  theme(
    axis.text.x = element_text(angle = 45, hjust = 1),
    legend.position = "bottom"
  )

# just _created metrics
mlos_longplot %>%
  filter(str_ends(metric, "_created")) %>%
  group_by(month, metric) %>%
  summarise(
    mean_value = mean(value, na.rm = TRUE),
    sd_value = sd(value, na.rm = TRUE),
    n = sum(!is.na(value)),
    se_value = sd_value / sqrt(n),
    .groups = "drop"
  ) %>%
  ggplot(aes(x = month, y = mean_value, group = metric, color = metric)) +
  geom_line(linewidth = 1) +
  geom_point(size = 2) +
  geom_errorbar(aes(ymin = mean_value - se_value, ymax = mean_value + se_value), 
                width = 0.1, alpha = 0.5) +
  geom_vline(
    xintercept = which(levels(mlos_longplot$month) == "month of"),
    color = "red",
    linetype = "dashed",
    linewidth = 0.3
  ) +
  labs(
    title = "Change in Metrics Over Five Months",
    x = "Month Relative to Training",
    y = "Mean Value"
  ) +
  theme_minimal() +
  theme(
    axis.text.x = element_text(angle = 45, hjust = 1),
    legend.position = "right",           # move to side
    legend.title = element_text(face = "bold"),
    legend.text = element_text(size = 10)
  ) +
  guides(color = guide_legend(ncol = 1))

# faceted line plots for each metric
mlos_longplot %>%
  group_by(month, metric) %>%
  summarise(mean_value = mean(value, na.rm = TRUE), .groups = "drop") %>%
  ggplot(aes(x = month, y = mean_value, group = 1)) +
  geom_line(color = "steelblue", linewidth = 1) +
  geom_point(size = 2, color = "steelblue") +
  facet_wrap(~ metric, scales = "free_y") +
  labs(
    title = "Average Metric Values Over Five Months",
    x = "Month Relative to Training",
    y = "Mean Value"
  ) +
  theme_minimal() +
  theme(axis.text.x = element_text(angle = 45, hjust = 1))

# normalize each metric by setting the month before as the baseline
mlos_deltas <- mlos_longplot %>%
  group_by(u._id, metric) %>%
  mutate(baseline = value[month == "month before"]) %>%
  ungroup() %>%
  mutate(change = value - baseline)

# relative change over five months: one plot per metric
mlos_deltas %>%
  ggplot(aes(x = month, y = change)) +
  geom_line(aes(group = u._id), alpha = 0.5, color = "gray60") +
  stat_summary(aes(group = 1), fun = mean, geom = "line", color = "red", linewidth = 1.2) +
  facet_wrap(~ metric, scales = "free_y") +
  labs(
    title = "Change from Baseline (Month Before Training)",
    x = "Month Relative to Training",
    y = "Change from Baseline"
  ) +
  theme_minimal() +
  theme(axis.text.x = element_text(angle = 45, hjust = 1))

# relative change over five months: all metrics on one plot
baseline <- mlos_longplot %>%
  filter(month == "month before") %>%
  select(u._id, metric, baseline_value = value)

mlos_deltas <- mlos_longplot %>%
  left_join(baseline, by = c("u._id", "metric")) %>%
  mutate(
    delta = value - baseline_value,
    rel_change = (value - baseline_value) / baseline_value
  )

mlos_deltas %>%
  group_by(month, metric) %>%
  summarise(mean_delta = mean(delta, na.rm = TRUE)) %>%
  ggplot(aes(x = month, y = mean_delta, group = metric, color = metric)) +
  geom_line(linewidth = 1) +
  geom_hline(yintercept = 0, linetype = "dashed") +
  labs(
    title = "Change in Metrics Relative to Month Before Training",
    x = "Month",
    y = "Mean Change (Delta)"
  ) +
  theme_minimal()

# descriptives of relative change 
mlos_relative <- mlos_longplot %>%
  group_by(u._id, metric) %>%
  mutate(baseline = value[month == "month before"]) %>%
  ungroup() %>%
  mutate(relative_change = (value - baseline) / baseline)  # proportion change

summary_relative <- mlos_relative %>%
  group_by(metric, month) %>%
  filter(!all(is.na(relative_change))) %>%   # drop groups with only NA
  summarise(
    mean_change   = mean(relative_change, na.rm = TRUE),
    median_change = median(relative_change, na.rm = TRUE),
    min_change    = min(relative_change, na.rm = TRUE),
    max_change    = max(relative_change, na.rm = TRUE),
    sd_change     = sd(relative_change, na.rm = TRUE),
    n             = sum(!is.na(relative_change)),
    .groups = "drop"
  )

# descriptives of monthly values themselves
summary_values <- mlos_longplot %>%
  group_by(metric, month) %>%
  summarise(
    mean_value   = mean(value, na.rm = TRUE),
    median_value = median(value, na.rm = TRUE),
    min_value    = min(value, na.rm = TRUE),
    max_value    = max(value, na.rm = TRUE),
    sd_value     = sd(value, na.rm = TRUE),
    n            = sum(!is.na(value)),
    .groups = "drop"
  ) %>%
  arrange(metric, month)

### bar plot: average values before and after ----
los_longplot %>%
  group_by(period, metric) %>%
  summarise(mean_value = mean(value, na.rm = TRUE), .groups = "drop") %>%
  ggplot(aes(x = metric, y = mean_value, fill = period)) +
  geom_col(position = position_dodge()) +
  labs(
    title = "Before vs After Training — Average Metrics",
    x = "Metric",
    y = "Mean Value"
  ) +
  theme_minimal() +
  theme(axis.text.x = element_text(angle = 45, hjust = 1))

### paired plot: individual-level changes ----
los_longplot %>%
  ggplot(aes(x = period, y = value, group = u._id)) +
  geom_line(alpha = 0.3, color = "gray") +
  geom_point(aes(color = period)) +
  facet_wrap(~ metric, scales = "free_y") +
  labs(
    title = "Individual-Level Change Before vs After Training",
    x = "",
    y = "Metric Value"
  ) +
  theme_minimal()

### boxplot: distribution before vs after ----
los_longplot %>%
  ggplot(aes(x = period, y = value, fill = period)) +
  geom_boxplot(alpha = 0.6) +
  facet_wrap(~ metric, scales = "free_y") +
  labs(title = "Distribution of Metrics Before vs After Training",
       x = "", y = "Value") +
  theme_minimal()

## increased/decreased/did not change before and after training ----

summarize_los_direction <- function(los_before, los_after, suffix_before, suffix_after) {
  
  # # doesn't pass the los_before and los_after arguments as it should
  # suffix_before <- sub("^.*(_.*)$", "\\1", deparse(substitute(los_before)))
  # suffix_after <- sub("^.*(_.*)$", "\\1", deparse(substitute(los_after)))
  
  los_longdiff <- los_before %>%
    inner_join(los_after, by = "u._id", suffix = c(suffix_before, suffix_after))
  
  for (col in numeric_cols) {
    los_longdiff[[paste0(col, "_diff")]] <- los_longdiff[[paste0(col, suffix_after)]] -
      los_longdiff[[paste0(col, suffix_before)]]
  }
  
  los_diff <- los_longdiff %>%
    select(u._id, ends_with("_diff")) %>%
    distinct()
  
  diff_cols <- names(los_diff)[grepl("_diff$", names(los_diff))]
  
  summary_los_direction <- los_diff %>%
    summarise(across(
      all_of(diff_cols),
      list(
        increased = ~ sum(. > 0, na.rm = TRUE),
        decreased = ~ sum(. < 0, na.rm = TRUE),
        no_change = ~ sum(. == 0, na.rm = TRUE)
      ),
      .names = "{.col}_{.fn}"
    )) %>%
    pivot_longer(
      cols = everything(),
      names_to = c("metric", "change_type"),
      names_sep = "_diff_",
      values_to = "count"
    ) %>%
    pivot_wider(
      names_from = change_type,
      values_from = count
    ) %>%
    mutate(n = increased + decreased + no_change)
  
  return(summary_los_direction)
}

# month before - month after training (2 month period)
summary_los_direction <- summarize_los_direction(los_before, los_after, "_before", "_after")

# convert to proportion of total
summary_los_direction_p <- summary_los_direction %>%
  mutate(increased = round(increased/n, 2),
         decreased = round(decreased/n, 2),
         no_change = round(no_change/n, 2))

# month before - month of (1 month period)
summary_los_direction_of <- summarize_los_direction(los_before, los_of, "_before", "_of")
# way too tight because training could've happened right at the end of the month

# month before - 2 months after training (3 month period)
summary_los_direction_2 <- summarize_los_direction(los_before, los_2_after, "_before", "_2_after")

# month before - 3 months after training (4 month period)
summary_los_direction_3 <- summarize_los_direction(los_before, los_3_after, "_before", "_3_after")

### diverging bar chart show how many users increased/decreased ----
# might overlook the majority of users showing no change
summary_los_direction_long <- summary_los_direction_long %>%
  group_by(metric) %>%
  mutate(prop = count / sum(count))

summary_los_direction_long %>%
  mutate(value = case_when(
    change_type == "decreased" ~ -count,
    change_type == "increased" ~ count,
    TRUE ~ 0
  )) %>%
  ggplot(., aes(x = metric, y = value, fill = change_type)) +
  geom_col() +
  labs(
    title = "Direction of Change per Metric",
    x = "Metric",
    y = "User Count",
    fill = "Change"
  ) +
  theme_minimal() +
  theme(axis.text.x = element_text(angle = 45, hjust = 1))


# event-aligned time series (months before/after *last* training regardless of months themselves)
los_aligned <- los_long %>%
  mutate(
    # convert month_label like "0924" → "2024-09-01"
    month_date = as.Date(paste0("20", substr(month_label, 3, 4), "-", substr(month_label, 1, 2), "-01")),
    
    # ensure training_date is Date type
    training_date = as.Date(last_training_date),
    
    # calculate difference in months between month_date and training_date
    months_from_training = interval(last_training_date, month_date) %/% months(1)
  )

# descriptives for creations based on months_from_training
los_aligned_summary <- los_aligned %>%
  group_by(months_from_training) %>%
  summarise(
    across(
      c(public_projects_created, private_projects_created, published_preprints_created),
      \(x) mean(x, na.rm = TRUE)
    )
  )

# visualize public_projects_created based on months_from_training
ggplot(los_aligned, aes(x = months_from_training, y = public_projects_created)) +
  geom_line(aes(group = Email), alpha = 0.3, color = "gray50") +
  stat_summary(fun = mean, geom = "line", color = "blue", linewidth = 0.5) +
  geom_vline(xintercept = 0, linetype = "dashed", color = "red") +
  labs(
    title = "Public Projects Created (Individual and Mean Trend)",
    x = "Months from Training",
    y = "Public Projects Created"
  ) +
  theme_minimal()

# logged actions ----
actions <- read_csv('~/Desktop/all_actions_1015.csv')

actions_subset <- osf_participants %>% 
  left_join(actions, by = c("u._id" = "user_id")) %>%
  select(inst, u._id, action, action_created, u.date_confirmed, first_training_date, last_training_date, postsurvey_date) %>%
  # days/weeks between training and given action
  mutate(
    days_from_first_training = as.numeric(difftime(action_created, first_training_date, units = "days")),
    days_from_last_training  = as.numeric(difftime(action_created, last_training_date,  units = "days"))
  )

actions_subset_i <- osf_participants %>% 
  inner_join(actions, by = c("u._id" = "user_id")) %>%
  select(inst, u._id, action, action_created, u.date_confirmed, first_training_date, last_training_date, postsurvey_date) %>%
  # days/weeks between training and given action
  mutate(
    days_from_first_training = as.numeric(difftime(action_created, first_training_date, units = "days")),
    days_from_last_training  = as.numeric(difftime(action_created, last_training_date,  units = "days"))
  )

write_sheet(actions_subset, trainings_url, sheet = "participant_actions")

actions_count <- actions_subset %>% 
  group_by(u._id) %>%
  summarize(action_count = n())

actions_type <- actions_subset %>% 
  group_by(action) %>%
  summarize(action_count = n())

# how many users have no actions?
users_no_actions <- actions_subset <- osf_participants %>% 
  anti_join(actions, by = c("u._id" = "user_id"))
# 95 users have no actions

## total actions before and after training ----

total_actions <- actions_subset %>%
  group_by(inst, u._id) %>%
  summarise(
    pre_first_actions  = sum(days_from_first_training < 0, na.rm = TRUE),
    post_first_actions = sum(days_from_first_training >= 0, na.rm = TRUE),
    .groups = "drop"
  )

total_actions_long <- total_actions %>%
  pivot_longer(
    cols = c(pre_first_actions, post_first_actions),
    names_to = "period",
    values_to = "n_actions"
  ) %>%
  mutate(
    period = case_when(
      grepl("pre", period)  ~ "pre",
      grepl("post", period) ~ "post"
    )
  )

summarize_total_actions <- function(df, pre_window_days = NULL, by_inst = NULL) {
  
  # Determine grouping for user-level counts
  grouping_vars <- if (!is.null(by_inst) && by_inst) c("inst", "u._id") else "u._id"
  
  df_summary <- df %>%
    group_by(across(all_of(grouping_vars))) %>%
    summarise(
      pre_first_actions = if (!is.null(pre_window_days)) {
        sum(
          days_from_first_training < 0 &
            days_from_first_training >= -pre_window_days,
          na.rm = TRUE
        )
      } else {
        sum(days_from_first_training < 0, na.rm = TRUE)
      },
      post_first_actions = sum(days_from_first_training >= 0, na.rm = TRUE),
      .groups = "drop"
    ) %>%
    pivot_longer(
      cols = c(pre_first_actions, post_first_actions),
      names_to = "period",
      values_to = "n_actions"
    ) %>%
    mutate(
      period = case_when(
        grepl("pre", period)  ~ ifelse(is.null(pre_window_days), "pre", paste0("pre_", pre_window_days, "d")),
        grepl("post", period) ~ "post"
      )
    )
  
  # Determine summary grouping (for computing mean/median per period)
  summary_group <- if (!is.null(by_inst) && by_inst) "inst" else NULL
  
  df_summary %>%
    group_by(across(all_of(summary_group)), period) %>%
    summarise(
      mean_actions   = mean(n_actions, na.rm = TRUE),
      median_actions = median(n_actions, na.rm = TRUE),
      sd_actions     = sd(n_actions, na.rm = TRUE),
      min_actions    = min(n_actions, na.rm = TRUE),
      max_actions    = max(n_actions, na.rm = TRUE),
      n_users        = n(),
      .groups = "drop"
    ) %>% 
    mutate(across(where(is.numeric), ~ ifelse(.x == 0, 0, round(.x, 2))))
}

summary_total_actions_3 <- summarize_total_actions(actions_subset, pre_window_days = 90)

summary_total_actions_6 <- summarize_total_actions(actions_subset, pre_window_days = 180)

summary_total_actions_6inst <- summarize_total_actions(actions_subset, pre_window_days = 180, by_inst = TRUE)

## LOS-specific actions ----
los_actions <- read_sheet(trainings_url, sheet = "los_actions") %>%
  select(definitely_LOS, maybe_LOS) %>%
  pivot_longer(cols = everything(), names_to = "classification", values_to = "action") %>%
  filter(!is.na(action)) %>%
  # just for checking numbers -- RERUN AFTER
  bind_rows(
    tibble(
      classification = "manual_add",
      action = c("embargo_initiated", "embargo_approved", "embargo_cancelled")
    )
  )

los_actions_subset <- actions_subset %>%
  filter(action %in% los_actions$action)

# mean actions
summary_total_los_actions_6 <- summarize_total_actions(los_actions_subset, pre_window_days = 180)
summary_total_los_actions_6inst <- summarize_total_actions(los_actions_subset, pre_window_days = 180, by_inst = TRUE)

## how many actions on active weeks since first_training_date ----
training_actions <- actions_subset %>%
  mutate(weeks_from_first_training = floor(days_from_first_training / 7),
         weeks_from_last_training = floor(days_from_last_training / 7)) %>%
  group_by(u._id, inst, first_training_date, weeks_from_first_training, last_training_date, weeks_from_last_training) %>%
  summarize(action_count = n(), .groups = 'drop')

ftraining_actions <- actions_subset %>%
  mutate(weeks_from_first_training = floor(days_from_first_training / 7)) %>%
  group_by(u._id, weeks_from_first_training, inst, first_training_date) %>%
  summarize(action_count = n(), .groups = 'drop')
# 7 users did 36 actions on the first_training_date

ltraining_actions <- actions_subset %>%
  mutate(weeks_from_last_training = floor(days_from_last_training / 7)) %>%
  group_by(u._id, weeks_from_last_training, inst, last_training_date) %>%
  summarize(action_count = n(), .groups = 'drop')
# 3 users did 8 actions on the last_training_date

# summarized (weekly) data, with total actions per week per user
training_long <- training_actions %>%
  select(u._id, inst, action_count, weeks_from_first_training, weeks_from_last_training) %>%
  pivot_longer(
    cols = starts_with("weeks_from_"),
    names_to = "anchor",
    names_prefix = "weeks_from_",
    values_to = "weeks_from_training"
  )

summary_training <- training_long %>%
  group_by(anchor, weeks_from_training) %>%
  summarize(mean_actions = mean(action_count, na.rm = TRUE), .groups = "drop")

### line plot: average weekly activity ----
# summary line plot for mean activity (average number of actions) given how many weeks from first/last training
ggplot(summary_training, aes(x = weeks_from_training, y = mean_actions, color = anchor)) +
  geom_line(linewidth = 1) +
  geom_vline(xintercept = 0, linetype = "dashed", color = "black") +
  scale_color_manual(values = c("first_training" = "#1f78b4", "last_training" = "#ffb81c"),
                     labels = c("First Training", "Last Training")) +
  xlim(-50, 50) +
  ylim(0, 200) +
  labs(
    title = "Average User Activity Anchored on First vs. Last Training",
    x = "Weeks from Training",
    y = "Mean Number of Actions",
    color = "Alignment"
  ) +
  theme_minimal() +
  theme(
    legend.position = "top",
    plot.title = element_text(face = "bold")
  )

### line plot + ribbon: average weekly activity with variability ----
# similar to above, but shows variability in ribbons
ggplot(training_long, aes(x = weeks_from_training, y = action_count, color = anchor, fill = anchor)) +
  stat_summary(fun = mean, geom = "line", size = 1) +
  stat_summary(fun.data = mean_se, geom = "ribbon", alpha = 0.2, color = NA) +
  geom_vline(xintercept = 0, linetype = "dashed", color = "black") +
  scale_color_manual(
    values = c("first_training" = "#1f78b4", "last_training" = "#ffb81c"),
    labels = c("First Training", "Last Training")
  ) +
  scale_fill_manual(
    values = c("first_training" = "#1f78b4", "last_training" = "#ffb81c"),
    labels = c("First Training", "Last Training")
  ) +
  xlim(-10, 50) +
  labs(
    title = "Average User Activity Around First vs. Last Training",
    x = "Weeks from Training",
    y = "Mean Number of Actions",
    color = "",
    fill = ""
  ) +
  theme_minimal() +
  theme(
    legend.position = "top",
    plot.title = element_text(face = "bold")
  )

# users' logged actions year before/after a training
actions_long <- actions_subset %>%
  pivot_longer(
    cols = starts_with("days_from_"),
    names_to = "anchor",
    names_prefix = "days_from_",
    values_to = "days_from_training"
  )

### density plot: distribution of actions over time around training ----
# density plot highlights when actions occur and how concentrated they are in the timeline
ggplot(actions_long, aes(x = days_from_training, fill = anchor, color = anchor)) +
  geom_density(alpha = 0.3) +
  geom_vline(xintercept = 0, linetype = "dashed", color = "black") +
  xlim(-365, 365) +
  labs(
    title = "Density of User Actions Around First vs. Last Training",
    x = "Days from Training",
    y = "Density",
    fill = "",
    color = ""
  ) +
  scale_color_manual(
    values = c("first_training" = "#1f78b4", "last_training" = "#ffb81c"),
    labels = c("First Training", "Last Training")
  ) +
  scale_fill_manual(
    values = c("first_training" = "#1f78b4", "last_training" = "#ffb81c"),
    labels = c("First Training", "Last Training")
  ) +
  theme_minimal() +
  theme(
    legend.position = "top",
    plot.title = element_text(face = "bold")
  )

## rates of activity before and after training ----
# confirmation --> training vs training --> present/data date)

summarize_actions_rates <- function(df, pre_window_days = NULL, by_inst = NULL, data_pull_date = Sys.Date(), rate_unit = c("daily", "weekly")) {
  
  rate_unit <- match.arg(rate_unit)
  scale_factor <- ifelse(rate_unit == "weekly", 7, 1)  # multiply daily rate by 7 if weekly
  
  # determine grouping for user-level counts
  grouping_vars <- if (!is.null(by_inst) && by_inst) c("inst", "u._id") else "u._id"
  
  df_rates <- df %>%
    # compute days difference
    mutate(
      days_from_first_training = as.numeric(difftime(action_created, first_training_date, units = "days")),
      # pre/post time windows (days)
      pre_period_days  = ifelse(is.null(pre_window_days), as.numeric(difftime(first_training_date, u.date_confirmed, units = "days")), 
                                pmin(pre_window_days, as.numeric(difftime(first_training_date, u.date_confirmed, units = "days")))),
      post_period_days = as.numeric(difftime(data_pull_date, first_training_date, units = "days"))
    ) %>%
    group_by(across(all_of(grouping_vars))) %>%
    summarise(
      pre_first_action_count  = sum(days_from_first_training < 0 & days_from_first_training >= -pre_period_days, na.rm = TRUE),
      post_first_action_count = sum(days_from_first_training >= 0, na.rm = TRUE),
      pre_period_days  = first(pre_period_days),
      post_period_days = first(post_period_days),
      .groups = "drop"
    ) %>%
    mutate(
      pre_first_action_rate  = pre_first_action_count  / pre_period_days  * scale_factor,
      post_first_action_rate = post_first_action_count / post_period_days * scale_factor
    )
  
  # compute summary stats
  summary_rates <- df_rates %>%
    pivot_longer(
      cols = c(pre_first_action_rate, post_first_action_rate),
      names_to = "period",
      values_to = "rate"
    ) %>%
    mutate(period = case_when(
      period == "pre_first_action_rate"  ~ ifelse(is.null(pre_window_days), "pre-first training", paste0("pre_", pre_window_days, "d")),
      period == "post_first_action_rate" ~ "post-first training",
      TRUE ~ NA_character_
    )) %>%
    group_by(across(if (!is.null(by_inst) && by_inst) "inst" else NULL), period) %>%
    summarise(
      mean_rate   = mean(rate, na.rm = TRUE),
      median_rate = median(rate, na.rm = TRUE),
      sd_rate     = sd(rate, na.rm = TRUE),
      min_rate    = min(rate, na.rm = TRUE),
      max_rate    = max(rate, na.rm = TRUE),
      n_users     = n(),
      .groups = "drop"
    ) %>%
    mutate(across(where(is.numeric), ~ ifelse(.x == 0, 0, round(.x, 2))))
  
  return(summary_rates)
}

# alternative
summarize_action_rates <- function(
    df,
    pre_window_days = NULL,          # number of days before training to include; NULL = all
    data_pull_date = Sys.Date(),     # end of post-training period
    by_inst = FALSE,                 # group by inst if TRUE
    rate_unit = c("daily", "weekly") # choose time unit for rate
) {
  
  rate_unit <- match.arg(rate_unit)
  scale_factor <- ifelse(rate_unit == "weekly", 7, 1)
  
  # determine user-level grouping
  grouping_vars <- if (by_inst) c("inst", "u._id") else "u._id"
  
  df_rates <- df %>%
    # compute days from first training
    mutate(days_from_first_training = as.numeric(difftime(action_created, first_training_date, units = "days"))) %>%
    # compute pre/post period denominators
    rowwise() %>%
    mutate(
      pre_period_days  = as.numeric(difftime(first_training_date, u.date_confirmed, units = "days")),
      pre_period_days  = if (!is.null(pre_window_days)) min(pre_period_days, pre_window_days) else pre_period_days,
      pre_period_days  = ifelse(pre_period_days <= 0, 1, pre_period_days),   # prevent division by 0
      post_period_days = as.numeric(difftime(data_pull_date, first_training_date, units = "days")),
      post_period_days = ifelse(post_period_days <= 0, 1, post_period_days)
    ) %>%
    ungroup() %>%
    group_by(across(all_of(grouping_vars))) %>%
    summarise(
      pre_first_action_count  = sum(days_from_first_training < 0 & days_from_first_training >= -pre_period_days, na.rm = TRUE),
      post_first_action_count = sum(days_from_first_training >= 0, na.rm = TRUE),
      pre_period_days  = first(pre_period_days),
      post_period_days = first(post_period_days),
      .groups = "drop"
    ) %>%
    mutate(
      pre_first_action_rate  = pre_first_action_count  / pre_period_days  * scale_factor,
      post_first_action_rate = post_first_action_count / post_period_days * scale_factor
    )
  
  # summary stats
  summary_rates <- df_rates %>%
    pivot_longer(
      cols = c(pre_first_action_rate, post_first_action_rate),
      names_to = "period",
      values_to = "rate"
    ) %>%
    mutate(period = case_when(
      period == "pre_first_action_rate"  ~ ifelse(is.null(pre_window_days), "pre-first training", paste0("pre_", pre_window_days, "d")),
      period == "post_first_action_rate" ~ "post-first training",
      TRUE ~ NA_character_
    )) %>%
    group_by(across(if (by_inst) "inst" else NULL), period) %>%
    summarise(
      mean_rate   = mean(rate, na.rm = TRUE),
      median_rate = median(rate, na.rm = TRUE),
      sd_rate     = sd(rate, na.rm = TRUE),
      min_rate    = min(rate, na.rm = TRUE),
      max_rate    = max(rate, na.rm = TRUE),
      n_users     = n(),
      .groups = "drop"
    ) %>%
    mutate(across(where(is.numeric), ~ ifelse(.x == 0, 0, round(.x, 2))))
  
  return(summary_rates)
}

# all actions
summary_rate_actions_6 <- summarize_action_rates(actions_subset %>% filter(!is.na(action_created)), pre_window_days = 180, data_pull_date = "2025-10-15", rate_unit = "daily")
# but it's slightly different than actions_rate_summary

# LOS actions
# don't need to remove NA actions because they are already filtered out when using the LOS action list
summary_rate_los_actions_6 <- summarize_action_rates(los_actions_subset, pre_window_days = 180, data_pull_date = "2025-10-15", rate_unit = "daily")
summary_rate_los_actions_6inst <- summarize_action_rates(los_actions_subset, pre_window_days = 180, by_inst = TRUE, data_pull_date = "2025-10-15", rate_unit = "daily")

actions_rates_180 <- actions_subset %>%
  filter(!is.na(action_created)) %>%
  mutate(
    # days from first training
    days_from_training = as.numeric(difftime(action_created, first_training_date, units = "days")),
    # post-training period until data pull date
    days_post_training = as.numeric(difftime("2025-10-15", first_training_date, units = "days"))
  ) %>%
  group_by(u._id) %>%
  summarise(
    # pre-training: only last 180 days
    pre_action_count  = sum(days_from_training < 0 & days_from_training >= -180, na.rm = TRUE),
    post_action_count = sum(days_from_training >= 0, na.rm = TRUE),
    days_post_training = first(days_post_training),
    .groups = "drop"
  ) %>%
  mutate(
    pre_action_rate  = pre_action_count / 180,           # denominator = 180 days
    post_action_rate = post_action_count / days_post_training,
    more_active      = post_action_rate > pre_action_rate
  )

# summary stats
actions_rate_summary_180 <- actions_rates_180 %>%
  select(pre_action_rate, post_action_rate) %>%
  pivot_longer(cols = everything(), names_to = "period", values_to = "rate") %>%
  group_by(period) %>%
  summarise(
    mean   = mean(rate, na.rm = TRUE),
    median = median(rate, na.rm = TRUE),
    sd     = sd(rate, na.rm = TRUE),
    Q1     = quantile(rate, 0.25, na.rm = TRUE),
    Q3     = quantile(rate, 0.75, na.rm = TRUE),
    min = min(rate, na.rm = TRUE),
    max = max(rate, na.rm = TRUE),
    n      = n(),
    .groups = "drop"
  )

# mapping actions to training topics ----
# will probably need to refine

# training topics with module number and (prelim) keywords
topics <- read_sheet(trainings_url, sheet="topic_keywords")

# only topics with keywords (Intro, Teaching, and Pedagogy are more general)
specific_topics <- topics %>% filter(!is.na(keyword))

# all unique actions
actions_types <- actions %>% distinct(action)

mapped_actions <- actions_types %>%
  rowwise() %>%
  mutate(matched_topics = list(unique(specific_topics$topic[str_detect(action, regex(specific_topics$keyword))]))) %>%
  unnest(cols = c(matched_topics))

# training dates including multiple trainings per group
# done above, but copied here for easier reference
trainings <- read_sheet(trainings_url, sheet="dates_topics")

## prereg actions for Prereg/RR trainings ----

# which trainings were about Prereg/RR?
# keep only last training for testing
ptrainings <- trainings %>% filter(str_detect(topic, "Prereg/RR")) %>%
  group_by(inst) %>%
  filter(training_date == max(training_date)) %>% ungroup()

pactions <- mapped_actions %>%
  filter(str_detect(matched_topics, "Prereg/RR"))

puser_allactions <- ptrainings %>%
  left_join(osf_participants %>% 
              select(u._id, inst, u.date_confirmed, u.is_active, u.is_spam, u.deleted), 
            by = "inst") %>%
  left_join(actions, by = c("u._id" = "user_id"))

puser_pactions <- puser_allactions %>%
  filter(action %in% pactions$action)

pperiods <- puser_pactions %>%
  mutate(days_from_training = as.numeric(difftime(action_created, training_date, units = "days"))) %>%
  mutate(weeks_from_training = floor(days_from_training / 7)) %>%
  mutate(time_period = case_when(
    days_from_training >= -28 & days_from_training < 0 ~ "Pre-training",
    days_from_training >= 0 & days_from_training <= 7 ~ "Immediate post-training",
    days_from_training >= 8 & days_from_training <= 30 ~ "Sustained post-training",
    days_from_training >= 31 ~ "Outside period post-training",
    days_from_training < -28 ~ "Outside period pre-training", 
    TRUE ~ NA
  ))
# none within the periods

pperiods_more <- puser_pactions %>%
  mutate(days_from_training = as.numeric(action_created - training_date)) %>%
  mutate(weeks_from_training = floor(days_from_training / 7)) %>%
  mutate(time_period = case_when(
    days_from_training >= -30 & days_from_training < 0 ~ "1 month pre-training",
    days_from_training >= 0 & days_from_training <= 30 ~ "1 month post-training",
    days_from_training >= 31 & days_from_training <= 100 ~ "3 months post-training",
    days_from_training >= 100 ~ "Outside period post-training",
    days_from_training < -30 ~ "Outside period pre-training", 
    TRUE ~ NA
  ))

ggplot(pperiods, aes(x = weeks_from_training)) +
  geom_histogram() +
  geom_vline(xintercept = 0, linetype = "dashed", color = "red")+
  xlim(-300, 45)
# +
# ylim(0, 50)

ggplot(pperiods, aes(x = weeks_from_training)) +
  geom_density(fill = "lightblue", alpha = 0.6) +
  geom_vline(xintercept = 0, linetype = "dashed", color = "red") +
  labs(
    title = "Density of Actions Around Training Dates",
    x = "Weeks from Training",
    y = "Density"
  ) +
  xlim(-100, 50) +
  theme_minimal()

ppost_actions <- pperiods %>%
  filter(days_from_training > 0)

ppost_summary <- ppost_actions %>%
  summarise(
    n = n(),
    mean_days = mean(days_from_training, na.rm = TRUE),
    median_days = median(days_from_training, na.rm = TRUE),
    sd_days = sd(days_from_training, na.rm = TRUE),
    min_days = min(days_from_training, na.rm = TRUE),
    max_days = max(days_from_training, na.rm = TRUE),
    Q1 = quantile(days_from_training, 0.25, na.rm = TRUE),
    Q3 = quantile(days_from_training, 0.75, na.rm = TRUE)
  )

quantile(ppost_actions$days_from_training, probs = c(0.25, 0.5, 0.75))
quantile(ppost_actions$weeks_from_training, probs = c(0.25, 0.5, 0.75))
# 25% post-training actions took place within 277 days/39 weeks
# 50% post-training actions took place within 291 days/41 weeks
# 75% post-training actions took place within 291 days/41 weeks

## all actions & trainings ----
# anchor on last training for now

# keep last training per group with topics
dates_topics <- trainings %>%
  group_by(inst) %>%
  filter(training_date == last_training_date) %>%
  ungroup()

overall_periods <- dates_topics %>%
  left_join(osf_participants %>% 
              select(u._id, inst, u.date_confirmed, u.is_active, u.is_spam, u.deleted), 
            by = "inst") %>%
  left_join(actions, by = c("u._id" = "user_id")) %>%
  mutate(days_from_training = as.numeric(difftime(action_created, last_training_date, units = "days"))) %>%
  mutate(weeks_from_training = floor(days_from_training / 7)) %>%
  mutate(time_period = case_when(
    days_from_training >= -28 & days_from_training < 0 ~ "Pre-training",
    days_from_training >= 0 & days_from_training <= 7 ~ "Immediate post-training",
    days_from_training >= 8 & days_from_training <= 30 ~ "Sustained post-training",
    days_from_training >= 31 ~ "Outside period post-training",
    days_from_training < -28 ~ "Outside period pre-training", 
    TRUE ~ NA
  ))

table(overall_periods$time_period)
# Outside period pre-training: 39046
# Pre-training: 248
# Immediate post-training: 28
# Sustained post-training: 106
# Outside period post-training: 3295

ggplot(overall_periods, aes(x = weeks_from_training, fill = inst)) +
  geom_density(alpha = 0.6) +
  geom_vline(xintercept = 0, linetype = "dashed", color = "red") +
  labs(
    title = "Density of Actions Around Training Dates",
    x = "Weeks from Training",
    y = "Density"
  ) +
  xlim(-4, 52) +
  theme_minimal()

# just looking at Syracuse: so many actions right before training?
ggplot(overall_periods %>% filter(inst == "Syracuse"), aes(x = weeks_from_training, fill = inst)) +
  geom_density(alpha = 0.6) +
  geom_vline(xintercept = 0, linetype = "dashed", color = "red") +
  labs(
    title = "Density of Actions Around Training Dates",
    x = "Weeks from Training",
    y = "Density"
  ) +
  xlim(-4, 4) +
  theme_minimal()

quantile(overall_periods$weeks_from_training, probs = c(0.25, 0.5, 0.75), na.rm = TRUE)
# 25% of actions happened 312 weeks before training
# 50% of actions happened 169 weeks before training
# 75% of actions happened 76 weeks before training

post_actions <- overall_periods %>%
  filter(days_from_training > 0)

quantile(post_actions$days_from_training, probs = c(0.25, 0.5, 0.75))
quantile(post_actions$weeks_from_training, probs = c(0.25, 0.5, 0.75))
# 25% of post-training actions happened after 92 days/13 weeks
# 50% of post-training actions happened after 218 days/31 weeks
# 75% of post-training actions happened after 240 days/34 weeks

### descriptives: all actions after training ----
post_summary <- post_actions %>%
  summarise(
    n = n(),
    mean_days = mean(days_from_training, na.rm = TRUE),
    median_days = median(days_from_training, na.rm = TRUE),
    sd_days = sd(days_from_training, na.rm = TRUE),
    min_days = min(days_from_training, na.rm = TRUE),
    max_days = max(days_from_training, na.rm = TRUE),
    Q1 = quantile(days_from_training, 0.25, na.rm = TRUE),
    Q3 = quantile(days_from_training, 0.75, na.rm = TRUE)
  )

### descriptives: all actions after training differentiated by inst ----
post_summary_inst <- post_actions %>%
  group_by(inst) %>%
  summarise(
    n = n(),
    mean_days = mean(days_from_training, na.rm = TRUE),
    median_days = median(days_from_training, na.rm = TRUE),
    sd_days = sd(days_from_training, na.rm = TRUE),
    min_days = min(days_from_training, na.rm = TRUE),
    max_days = max(days_from_training, na.rm = TRUE),
    Q1 = quantile(days_from_training, 0.25, na.rm = TRUE),
    Q3 = quantile(days_from_training, 0.75, na.rm = TRUE),
    .groups = "drop"
  )

## try mapping actions Cincinnati subset ----
cin_trainings <- trainings %>%
  filter(inst == "Cincinnati")
# 8 dates (7 trainings, 1 post-survey)

cin_actions <- osf_participants %>%
  filter(inst == "Cincinnati") %>%
  select(inst, u._id, u.date_confirmed, u.is_active, u.is_spam, u.deleted) %>%
  left_join(actions, by = c("u._id" = "user_id"))
# 22 users with 2405 actions

### plot: UCincinnati users' actions relative to multiple training dates ---- 
# timeline per participant
# restricted timeframe to November 2024-present
ggplot(cin_actions, aes(x = action_created, y = u._id)) +
  geom_jitter(aes(color = "action"), alpha = 0.3) +
  geom_vline(data = cin_trainings, aes(xintercept = as.numeric(training_date), color = "training"),
             linetype = "dashed") +
  scale_color_manual(values = c("action" = "grey40", "training" = "blue")) +
  scale_x_datetime(
    limits = as.POSIXct(c("2024-11-01", "2025-10-01"))
  ) +
  labs(x = "Date", y = "Participant", title = "Actions relative to training dates") +
  theme_minimal()

cin_actions_aligned <- cin_actions %>%
  left_join(cin_trainings, by = "inst") %>%
  mutate(days_from_training = as.numeric(difftime(action_created, training_date, units = "days")))

# plot density of actions relative to training date
# not complete
ggplot(cin_actions_aligned, aes(x = days_from_training)) +
  geom_histogram(binwidth = 7, fill = "skyblue", color = "white") +
  geom_vline(xintercept = 0, color = "red", linetype = "dashed") +
  labs(
    x = "Days relative to training date",
    y = "Number of actions",
    title = "Action timing relative to training events"
  ) +
  theme_minimal()
