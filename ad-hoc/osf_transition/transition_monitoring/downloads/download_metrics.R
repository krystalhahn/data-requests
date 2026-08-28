## weekly metrics ----
get_download_metrics <- function(download_data_path, cadence, start, end) {
  
  library(readr)
  library(dplyr)
  library(tidyr)
  
  downloads_all <- read_csv(download_data_path)
  
  if (cadence == "weekly") {
    
    start_week <- as.POSIXct(start, tz = "UTC")
    end_week <- as.POSIXct(end, tz = "UTC")
    
    # generate weekly start dates
    week_starts <- seq(
      from = start_week,
      to = end_week - lubridate::days(7),
      by = "1 week"
    )
    
    # function to calculate metrics for one week
    get_one_week <- function(week_start) {
      
      week_end <- week_start + lubridate::days(7)
      
      downloads <- downloads_all %>%
        filter(
          created >= week_start,
          created < week_end
        )
      
      zip_levels <- c(TRUE, FALSE, NA)
      
      # by download type ----
      
      by_type <- downloads %>%
        mutate(
          zip_completed = factor(
            zip_completed,
            levels = zip_levels
          )
        ) %>%
        group_by(download_type, zip_completed) %>%
        summarise(
          count = n(),
          size_gb = round(sum(size_bytes, na.rm = TRUE) / 1e9, 2),
          .groups = "drop"
        ) %>%
        mutate(
          metric = "download_type",
          attribute = download_type,
          attribute_2 = case_when(
            zip_completed == TRUE ~ "zip_completed",
            zip_completed == FALSE ~ "zip_not_completed",
            is.na(zip_completed) ~ NA_character_
          )
        ) %>%
        select(metric, attribute, attribute_2, count, size_gb)
      
      # by user type ----
      
      by_user_type <- downloads %>%
        mutate(
          user_type = case_when(
            is.na(user_guid) ~ "non-user",
            !is.na(user_guid) ~ "user"
          ),
          zip_completed = factor(
            zip_completed,
            levels = zip_levels
          )
        ) %>%
        group_by(user_type, zip_completed) %>%
        summarise(
          count = n(),
          size_gb = round(sum(size_bytes, na.rm = TRUE) / 1e9, 2),
          .groups = "drop"
        ) %>%
        mutate(
          metric = "user_type",
          attribute = user_type,
          attribute_2 = case_when(
            zip_completed == TRUE ~ "zip_completed",
            zip_completed == FALSE ~ "zip_not_completed",
            is.na(zip_completed) ~ NA_character_
          )
        ) %>%
        select(metric, attribute, attribute_2, count, size_gb)
      
      # by resource type ----
      
      by_resource_type <- downloads %>%
        mutate(
          resource_type = case_when(
            resource_type == "osf.node" ~ "node",
            resource_type == "osf.registration" ~ "registration",
            resource_type == "osf.preprint" ~ "preprint"
          ),
          zip_completed = factor(
            zip_completed,
            levels = zip_levels
          )
        ) %>%
        group_by(resource_type, zip_completed) %>%
        summarise(
          count = n(),
          size_gb = round(sum(size_bytes, na.rm = TRUE) / 1e9, 2),
          .groups = "drop"
        ) %>%
        mutate(
          metric = "resource_type",
          attribute = resource_type,
          attribute_2 = case_when(
            zip_completed == TRUE ~ "zip_completed",
            zip_completed == FALSE ~ "zip_not_completed",
            is.na(zip_completed) ~ NA_character_
          )
        ) %>%
        select(metric, attribute, attribute_2, count, size_gb)
      
      # by storage region ----
      
      by_storage_region <- downloads %>%
        mutate(
          zip_completed = factor(
            zip_completed,
            levels = zip_levels
          )
        ) %>%
        group_by(storage_region, zip_completed) %>%
        summarise(
          count = n(),
          size_gb = round(sum(size_bytes, na.rm = TRUE) / 1e9, 2),
          .groups = "drop"
        ) %>%
        mutate(
          metric = "storage_region",
          attribute = storage_region,
          attribute_2 = case_when(
            zip_completed == TRUE ~ "zip_completed",
            zip_completed == FALSE ~ "zip_not_completed",
            is.na(zip_completed) ~ NA_character_
          )
        ) %>%
        select(metric, attribute, attribute_2, count, size_gb)
      
      # by storage provider ----
      
      by_storage_provider <- downloads %>%
        mutate(
          zip_completed = factor(
            zip_completed,
            levels = zip_levels
          )
        ) %>%
        group_by(storage_provider, zip_completed) %>%
        summarise(
          count = n(),
          size_gb = round(sum(size_bytes, na.rm = TRUE) / 1e9, 2),
          .groups = "drop"
        ) %>%
        complete(
          storage_provider,
          zip_completed,
          fill = list(
            count = 0,
            size_gb = 0
          )
        ) %>%
        mutate(
          metric = "storage_provider",
          attribute = storage_provider,
          attribute_2 = case_when(
            zip_completed == TRUE ~ "zip_completed",
            zip_completed == FALSE ~ "zip_not_completed",
            is.na(zip_completed) ~ NA_character_
          )
        ) %>%
        select(metric, attribute, attribute_2, count, size_gb)
      
      # combine metrics ----
      
      bind_rows(
        by_type,
        by_user_type,
        by_resource_type,
        by_storage_region,
        by_storage_provider
      ) %>%
        pivot_longer(
          cols = c(count, size_gb),
          names_to = "measure",
          values_to = "value"
        ) %>%
        mutate(
          week = format(week_start, "%Y-%m-%d")
        )
    }
    
    # calculate metrics for every week
    weekly_metrics <- bind_rows(
      lapply(week_starts, get_one_week)
    )
    
    # put weeks into columns
    weekly_metrics <- weekly_metrics %>%
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
    
    return(weekly_metrics)
  }
}

# generate metrics ----
download_metrics <- get_download_metrics(
  download_data_path = "~/Desktop/download_events_0822.csv",
  cadence = "weekly",
  start = "2026-08-09",
  end = "2026-08-23"
)