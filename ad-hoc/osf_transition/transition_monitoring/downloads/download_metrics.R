get_download_metrics <- function(
    download_data_path,
    cadence,
    start,
    end,
    cumulative = FALSE
) {
  
  library(readr)
  library(dplyr)
  library(tidyr)
  library(lubridate)
  
  downloads_all <- read_csv(download_data_path)
  
  # helper function: download count buckets ----
  
  get_count_bucket <- function(x) {
    case_when(
      x < 10 ~ "<10 downloads",
      x < 50 ~ "10+ downloads",
      x < 100 ~ "50+ downloads",
      x < 500 ~ "100+ downloads",
      x >= 500 ~ "500+ downloads"
    )
  }
  
  # helper function: download size buckets ----
  
  get_size_bucket <- function(x) {
    case_when(
      is.na(x) ~ "NA GB",
      x < 5 ~ "<5 GB",
      x < 10 ~ "5+ GB",
      x < 25 ~ "10+ GB",
      x < 50 ~ "25+ GB",
      x < 100 ~ "50+ GB",
      x < 500 ~ "100+ GB",
      x >= 500 ~ "500+ GB"
    )
  }
  
  # helper function: aggregate download metric ----
  
  aggregate_download_metric <- function(
    data,
    group_var,
    metric_name,
    complete_combinations = FALSE,
    include_percent = FALSE
  ) {
    
    result <- data %>%
      mutate(
        zip_completed = factor(
          zip_completed,
          levels = c(TRUE, FALSE, NA)
        )
      ) %>%
      group_by(.data[[group_var]], zip_completed) %>%
      summarise(
        count = n(),
        size_gb = round(
          sum(size_bytes, na.rm = TRUE) / 1e9,
          2
        ),
        .groups = "drop"
      )
    
    if (complete_combinations) {
      result <- result %>%
        complete(
          !!sym(group_var),
          zip_completed,
          fill = list(
            count = 0,
            size_gb = 0
          )
        )
    }
    
    if (include_percent) {
      result <- result %>%
        mutate(
          percent_total = round(
            count / sum(count) * 100,
            2
          )
        )
    }
    
    result %>%
      rename(attribute = all_of(group_var)) %>%
      mutate(
        metric = metric_name,
        attribute_2 = case_when(
          zip_completed == TRUE ~ "zip_completed",
          zip_completed == FALSE ~ "zip_not_completed",
          is.na(zip_completed) ~ NA_character_
        )
      ) %>%
      select(
        metric,
        attribute,
        attribute_2,
        count,
        size_gb,
        any_of("percent_total")
      )
  }
  
  # helper function: aggregate bucket metric ----
  
  aggregate_bucket_metric <- function(
    data,
    id_var,
    bucket_var,
    metric_name,
    bucket_levels
  ) {
    
    # calculate total downloads and total size for each user/project before assigning it to a bucket
    totals <- data %>%
      filter(!is.na(.data[[id_var]])) %>%
      group_by(.data[[id_var]]) %>%
      summarise(
        total_count = n(),
        total_gb = if (all(is.na(size_bytes))) {
          NA_real_
        } else {
          sum(size_bytes, na.rm = TRUE) / 1e9
        },
        .groups = "drop"
      )
    
    # assign each user/project to a bucket
    totals <- totals %>%
      mutate(
        attribute = if (bucket_var == "count") {
          get_count_bucket(total_count)
        } else {
          get_size_bucket(total_gb)
        },
        attribute = factor(
          attribute,
          levels = bucket_levels
        )
      )
    
    # count users/projects in each bucket
    # complete() ensures buckets with zero users/projects are retained as 0
    totals %>%
      count(attribute, name = "value") %>%
      complete(
        attribute = factor(
          bucket_levels,
          levels = bucket_levels
        ),
        fill = list(value = 0)
      ) %>%
      mutate(
        metric = metric_name,
        attribute = as.character(attribute),
        attribute_2 = NA_character_,
        measure = "count"
      ) %>%
      select(
        metric,
        attribute,
        attribute_2,
        measure,
        value
      )
  }
  
  # weekly metrics ----
  
  if (cadence == "weekly") {
    
    start_week <- as.POSIXct(start, tz = "UTC")
    end_week <- as.POSIXct(end, tz = "UTC")
    
    week_starts <- seq(
      from = start_week,
      to = end_week - days(7),
      by = "1 week"
    )
    
    # calculate metrics for each week ----
    
    get_one_week <- function(week_start) {
      
      week_end <- week_start + days(7)
      
      # choose weekly vs. cumulative metrics ----
      if (cumulative) {
        downloads <- downloads_all %>%
          filter(
            created >= start_week,
            created < week_end
          )
      } else {
        downloads <- downloads_all %>%
          filter(
            created >= week_start,
            created < week_end
          )
      }
      
      # by download type ----
      
      by_download_type <- aggregate_download_metric(
        downloads,
        "download_type",
        "download_type",
        include_percent = TRUE
      )
      
      # by user type ----
      
      by_user_type <- downloads %>%
        mutate(
          user_type = case_when(
            is.na(user_guid) ~ "non-user",
            !is.na(user_guid) ~ "user"
          )
        ) %>%
        aggregate_download_metric(
          "user_type",
          "user_type",
          include_percent = TRUE
        )
      
      # by resource type ----
      
      by_resource_type <- downloads %>%
        mutate(
          resource_type = case_when(
            resource_type == "osf.node" ~ "node",
            resource_type == "osf.registration" ~ "registration",
            resource_type == "osf.preprint" ~ "preprint"
          )
        ) %>%
        aggregate_download_metric(
          "resource_type",
          "resource_type",
          include_percent = TRUE
        )
      
      # by storage region ----
      
      by_storage_region <- aggregate_download_metric(
        downloads,
        "storage_region",
        "storage_region",
        include_percent = TRUE
      )
      
      # by storage provider ----
      
      by_storage_provider <- aggregate_download_metric(
        downloads,
        "storage_provider",
        "storage_provider",
        complete_combinations = TRUE,
        include_percent = TRUE
      )
      
      # user buckets ----
      
      by_user_bucket_count <- aggregate_bucket_metric(
        downloads,
        id_var = "user_guid",
        bucket_var = "count",
        metric_name = "user_bucket_count",
        bucket_levels = c(
          "<10 downloads",
          "10+ downloads",
          "50+ downloads",
          "100+ downloads",
          "500+ downloads"
        )
      )
      
      by_user_bucket_size <- aggregate_bucket_metric(
        downloads,
        id_var = "user_guid",
        bucket_var = "size",
        metric_name = "user_bucket_size",
        bucket_levels = c(
          "<5 GB",
          "5+ GB",
          "10+ GB",
          "25+ GB",
          "50+ GB",
          "100+ GB",
          "500+ GB",
          "NA GB"
        )
      )
      
      # project buckets ----
      
      project_downloads <- downloads %>%
        filter(resource_type == "osf.node")
      
      by_project_bucket_count <- aggregate_bucket_metric(
        project_downloads,
        id_var = "resource_guid",
        bucket_var = "count",
        metric_name = "project_bucket_count",
        bucket_levels = c(
          "<10 downloads",
          "10+ downloads",
          "50+ downloads",
          "100+ downloads",
          "500+ downloads"
        )
      )
      
      by_project_bucket_size <- aggregate_bucket_metric(
        project_downloads,
        id_var = "resource_guid",
        bucket_var = "size",
        metric_name = "project_bucket_size",
        bucket_levels = c(
          "<5 GB",
          "5+ GB",
          "10+ GB",
          "25+ GB",
          "50+ GB",
          "100+ GB",
          "500+ GB",
          "NA GB"
        )
      )
      
      # combine metrics ----
      
      # regular metrics are converted to long format first
      # bucket metrics are already in long format
      regular_metrics <- bind_rows(
        by_download_type,
        by_user_type,
        by_resource_type,
        by_storage_region,
        by_storage_provider
      ) %>%
        pivot_longer(
          cols = c(count, size_gb, percent_total),
          names_to = "measure",
          values_to = "value"
        )
      
      bucket_metrics <- bind_rows(
        by_user_bucket_count,
        by_user_bucket_size,
        by_project_bucket_count,
        by_project_bucket_size
      )
      
      bind_rows(
        regular_metrics,
        bucket_metrics
      ) %>%
        mutate(
          week = format(week_start, "%Y-%m-%d")
        )
    }
    
    # calculate metrics for every week ----
    
    bind_rows(
      lapply(week_starts, get_one_week)
    ) %>%
      select(
        metric,
        attribute,
        attribute_2,
        measure,
        week,
        value
      ) %>%
      pivot_wider(
        names_from = week,
        values_from = value
      )
  }
}

# generate weekly metrics ----
download_metrics <- get_download_metrics(
  "~/Desktop/download_events_0822.csv",
  "weekly",
  "2026-08-09",
  "2026-08-23",
  cumulative = FALSE
)

# generate cumulative metrics ----
download_metrics_cumulative <- get_download_metrics(
  "~/Desktop/download_events_0822.csv",
  "weekly",
  "2026-08-09",
  "2026-08-23",
  cumulative = TRUE
)