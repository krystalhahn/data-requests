library(readr)
library(tidyverse)
library(dplyr)
library(stringr)
library(googlesheets4)
library(googledrive)
library(readxl)
library(tibble)
library(purrr)
library(tidyr)
gs4_auth(email = "krystal@cos.io", cache = FALSE)
drive_auth()

# get webinar files from Google Drive ----
main_folder <- drive_get("OSF 101")

all_files <- drive_ls(main_folder, recursive = TRUE)

month_folders <- drive_ls(main_folder, type = "folder")

# getting all CSVs with "attend" in the name
# observed "attendee" or "attendance" in different file names --- not consistent
attendee_files <- month_folders %>%
  mutate(files = map(id, ~ drive_ls(as_id(.x)))) %>%
  unnest(files, names_sep = "_") %>%  # add prefix to avoid name collision
  filter(
    grepl("attendee", files_name, ignore.case = TRUE),
    grepl("\\.csv$", files_name, ignore.case = TRUE)
  ) %>%
  transmute(
    folder_name = name,          # folder name from parent folder
    file_name = files_name,      # file name inside
    file_id = files_id,          # file ID
    file_drive_resource = files_drive_resource
  )

## find attendee files within each Google Drive month folder ----
find_attendee_file <- function(folder_id) {
  
  files <- drive_ls(as_id(folder_id))
  
  # look for CSV with "attend" in the current folder
  csv_match <- files %>%
    filter(grepl("attend", name, ignore.case = TRUE),
           grepl("\\.csv$", name, ignore.case = TRUE))
  
  if (nrow(csv_match) > 0) {
    return(csv_match %>% 
             select(name, id, drive_resource))
  }
  
  # check each item in the folder to see if it's a subfolder
  sub_results <- map_dfr(files$id, function(sub_id) {
    subfiles <- tryCatch(
      drive_ls(as_id(sub_id)),
      error = function(e) NULL
    )
    
    if (!is.null(subfiles)) {
      subfiles %>%
        filter(grepl("attend", name, ignore.case = TRUE),
               grepl("\\.csv$", name, ignore.case = TRUE)) %>%
        select(name, id, drive_resource)
    } else {
      tibble()  # return empty tibble if drive_ls failed
    }
  })
  
  if (nrow(sub_results) > 0) return(sub_results)
  
  # if still nothing, look for non-CSV files (gsheets, xlsx) in current folder
  gsheet_match <- files %>%
    filter(grepl("attend", name, ignore.case = TRUE)) %>%
    select(name, id, drive_resource)
  
  if (nrow(gsheet_match) > 0) return(gsheet_match)
  
  # if nothing found, return NA
  tibble(
    name = NA_character_,
    id = NA_character_,
    drive_resource = NA
  )
}

## loop through month folders ----
find_webinar_files <- function(main_folder) {
  main_folder <- drive_get(main_folder)
  
  month_folders <- drive_ls(main_folder, type = "folder")
  
  attendee_files <- month_folders %>%
    mutate(file_info = map(id, find_attendee_file)) %>%
    unnest(file_info, names_sep = "_") %>%   # will prefix with file_info_
    transmute(
      month_folder = name,
      file_name = file_info_name,
      file_id = file_info_id,
      file_drive_resource = file_info_drive_resource
    ) %>%
    # if attendee file was found, mark as attendees
    # if attendee file was not found, leave as NA to be filled in
    mutate(
      file_type = ifelse(!is.na(file_name), "attendees", NA_character_)
    )
  return(attendee_files)
}

## pull for 2025 and 2024 webinars ----
webinars_2025 <- find_webinar_files("OSF 101")

webinars_2025 <- webinars_2025 %>%
  filter(!month_folder %in% c("Analysis ", "April 14th", "Jun 9", "Oct 10"))

# dups:
# Apr 14 vs April 14th: they look the same, either work
# Oct 10 vs Oct 13: Oct 10 is some special edition webinar, keep Oct 13
# Jun 9 vs June 9th: files are diff name and size, need to check
# they were different because of the file format -- as plain CSVs, same size and content
# keep June 9th
# reformatted as plain CSVs instead of delimited CSV
jun9 <- read_csv("~/Downloads/Jun9_89235524776 - Attendee Report (3).csv")
june9th <- read_csv("~/Downloads/June9th_attendee_89235524776_2025_06_09.csv")
# all.equal(jun9, june9th)
# # [1] "Attributes: < Component “spec”: Component “cols”: Length mismatch: comparison on first 1 components >"
# # [2] "Length mismatch: comparison on first 1 components"                                                    
# # [3] "Component “Attendee Report”: 960 string mismatches"     

jun_diff1 <- setdiff(jun9, june9th)
jun_diff2 <- setdiff(june9th, jun9)

webinars_2024 <- find_webinar_files("OSF 101 (Marketing folder)") 

# to add specific files that did not get captured in the find_webinar_files()
## September 2024 has two "Attendee Report"'s but they seem to be the same file...
### used "Attendee Report" CSV
## October 2024 file was pulled from subfolder, but that is not the usual OSF 101: "OSF 101: Deep Dive in Registrations and Prereg..."
### need "10.14 OSF 101.xlsx"
manual_files <- tribble(
  ~month_folder, ~file_name, ~file_type,
  "June 2024", "Registrants June OSF 101 Webinar_clean.xlsx", "registrants",
  "July 2024", "osf 101 july 2024 registrants.xlsx", "attendees",
  "August 2024", "OSF 101 Webianr August 2024.xlsx", "registrants",
  "October 2024", "10.14 OSF 101.xlsx", "attendees"
) %>%
  mutate(file_info = map(file_name, drive_get)) %>%
  unnest(file_info, names_sep = "_") %>%
  transmute(
    month_folder,
    file_name,
    file_id = file_info_id,
    file_drive_resource = file_info_drive_resource,
    file_type = file_type
  )

# add to 2024 webinars file info
webinars_2024 <- webinars_2024 %>%
  filter(month_folder != "October 2024") %>%
  bind_rows(., manual_files) %>%
  filter(file_name != "FOR SF osf 101 3.24 - attendee report.xlsx")

# dups:
# March 2024: keep "osf 101...", the other one looks like a subset
# issues: no attendee file
# August 2024: "OSF 101 Webianr August 2024.xlsx" looks like it, but no df_pre part
# July 2024: "osf 101 july 2024 registrants.xlsx" looks like it, but no df_pre part 
# June 2024: "Registrants June OSF 101 Webinar_clean.xlsx" looks like it, but no df_pre part 
# NOTE: what is the difference between attendee file and registrant files? sometimes they both exist?

# create universal month identifiers
foldername_to_month <- c(
  "March 2024" = "0324",
  "April 2024" = "0424", 
  "May 2024" = "0524",
  "June 2024" = "0624", 
  "July 2024" = "0724", 
  "August 2024" = "0824", 
  "September 2024" = "0924", 
  "October 2024" = "1024",
  "November 2024" = "1124",
  "Jan 13" = "0125",
  "Feb 10" = "0225", 
  "Mar 10" = "0325", 
  "Apr 14" = "0425",
  "May 12th " = "0525",
  "June 9th" = "0625",
  "July 14th" = "0725",
  "Aug 11" = "0825",
  "Sept 8" = "0925",
  "Oct 13" = "1025"
)

## merge 2024 and 2025 webinar file info ----
webinar_filenames <- webinars_2025 %>%
  bind_rows(webinars_2024) %>%
  mutate(month = foldername_to_month[month_folder],
         mime_type = map_chr(file_drive_resource, "mimeType"))

# get actual webinar/attendee data ----

## convert to plain text lines depending on original file type ----
get_webinar_text <- function(file_name, file_id, mime_type, month) {
  # create temporary file for local download
  tmp <- tempfile(fileext = ".csv")
  
  # CSV
  if (grepl("\\.csv$", file_name, ignore.case = TRUE)) {
    drive_download(as_id(file_id), path = tmp, overwrite = TRUE)
    return(readLines(tmp, warn = FALSE))
  }
  
  # Google Sheet
  else if (grepl("google", mime_type, ignore.case = TRUE)) {
    df <- read_sheet(as_sheets_id(file_id)) %>% 
      # most columns are lists for some reason, need them to be character vectors
      mutate(across(where(is.list), ~ as.character(.x)))
    tmp <- tempfile(fileext = ".csv")
    readr::write_csv(df, tmp)
    return(readLines(tmp, warn = FALSE))
  }
  
  # Excel (.xls / .xlsx)
  else if (grepl("excel", mime_type, ignore.case = TRUE) || grepl("\\.xlsx?$", file_name, ignore.case = TRUE)) {
    tmp_xlsx <- tempfile(fileext = ".xlsx")
    drive_download(as_id(file_id), path = tmp_xlsx, overwrite = TRUE)
    df <- readxl::read_excel(tmp_xlsx)
    tmp <- tempfile(fileext = ".csv")
    readr::write_csv(df, tmp)
    return(readLines(tmp, warn = FALSE))
  }
  
  # Unsupported file type
  else {
    stop("Unsupported file type: ", month, ", ", file_name)
  }
}

# check original files converted to text lines properly
get_test_list <- pmap(
  list(
    file_name = webinar_filenames$file_name,
    file_id = webinar_filenames$file_id,
    mime_type = webinar_filenames$mime_type,
    month = webinar_filenames$month
  ),
  get_webinar_text
)

## split data into webinar and attendee data and clean up ----
read_webinar_csv <- function(lines, month) {
  
  # ensure that lines are character vectors
  lines <- unlist(lines)
  
  # remove leading/trailing whitespace and empty lines
  lines <- lines[trimws(lines) != ""]
  
  # check if first line starts with number (ex. "83809858936 - Attendee Report") and drop if so
  if (grepl("^[0-9]", trimws(lines[1]))) {
    message("Removing first line because it starts with a number: ", lines[1])
    lines <- lines[-1]
  }
  
  # setting "Attended" line as the marker for where the attendee data starts (df_post)
  start_line <- tail(which(grepl("^Attended", lines, ignore.case = TRUE)), 1)
  if (length(start_line) == 0) stop(paste0("Attendee data not found in the file."))
  
  # split pre- and post-marker lines
  # set webinar data (df_pre) empty if there are no host or panelist details (no webinar data either)
  if (!any(grepl("Host Details|Panelist Details", lines, ignore.case = TRUE))) {
    pre_lines <- character(0)
    post_lines <- lines[start_line:length(lines)]
  } else {
    pre_lines  <- lines[1:(start_line - 1)]
    # add comma to end of first line if there is none, to prevent complications in read_csv()
    if (!grepl(",$", pre_lines[1])) {
      pre_lines[1] <- paste0(pre_lines[1], ",")
    }
    post_lines <- lines[start_line:length(lines)]
  }
  
  # convert lines back to data frames
  df_pre  <- if(length(pre_lines) > 0) read_csv(I(pre_lines), col_names = FALSE) else tibble()
  df_post <- if(length(post_lines) > 0) read_csv(I(post_lines), col_names = TRUE) else tibble() 
  
  # clean up post-marker section (attendee data)
  # df_post either has 9 or fewer columns (registrant data) or 18 columns (attendee data - ideal, most cases)
  # if it is registrant data (ncol <= 9)
  if (ncol(df_post) <= 9) {
    clean_df_post <- df_post %>%
      # replace "--" with NA
      mutate(across(everything(), ~ na_if(.x, "--"))) %>%
      # rename columns to usable formats
      rename_with(~ gsub(" ", "_", tolower(.x))) %>%
      rename(
        country_region   = `country/region`,
        self_description = any_of(c("what_best_describes_you?", "what_best_describe_you?"))) %>%
      # clean up values and value classes
      mutate(
        attended = ifelse(attended == "Yes", T, F),
        email = tolower(email),
        self_description = case_when(
          startsWith(self_description, "I am a graduate student") ~ 1,
          self_description == "I am a librarian" ~ 2,
          self_description == "I am a person who does research" ~ 3,
          self_description == "I help manage a research community" ~ 4,
          self_description == "I help researchers with data" ~ 5,
          self_description == "Other" ~ 6
        )
      ) %>%
      select(where(~ !all(is.na(.x))))
  } else {
    # if it is attendee data (ncol = 18)
    clean_df_post <- df_post %>%
      # # replace "--" with NA
      mutate(across(everything(), ~ na_if(.x, "--"))) %>%
      # rename columns to usable formats
      rename_with(~ gsub(" ", "_", tolower(.x))) %>%
      rename(
        full_name           = any_of("user_name_(original_name)"),
        country_region      = `country/region`,
        time_in_session_m   = `time_in_session_(minutes)`,
        self_description    = any_of(c("what_best_describes_you?", "what_best_describe_you?")),
        tou_pp              = `terms_of_use_and_privacy_policy`,
        country_region_name = `country/region_name`) %>%
      # clean up values and value classes
      mutate(
        attended = ifelse(attended == "Yes", T, F),
        email = tolower(email),
        # # need to inspect to see if all the datetime strings are consistently formatted
        # across(contains("_time"), ~ as.POSIXct(.x, format = "%b %d, %Y %H:%M:%S")),
        time_in_session_m = as.numeric(time_in_session_m),
        is_guest = ifelse(is_guest == "Yes",
                          T,
                          ifelse(is_guest == "No", F, NA)),
        self_description = case_when(
          startsWith(self_description, "I am a graduate student") ~ 1,
          self_description == "I am a librarian" ~ 2,
          self_description == "I am a person who does research" ~ 3,
          self_description == "I help manage a research community" ~ 4,
          self_description == "I help researchers with data" ~ 5,
          self_description == "Other" ~ 6
        ),
        tou_pp = ifelse(is.na(tou_pp), NA, T) #
      ) %>%
      select(where(~ !all(is.na(.x))))
  }
  
  # clean up pre-marker section (webinar data)
  # if there are no rows, set clean_df_pre as empty tibble
  if (nrow(df_pre) == 0) {
    clean_df_pre <- tibble()
  } else {
    # if there are pre-marker rows
    # trim to only rows up to "Host Details" in column 1
    host_row <- which(df_pre[[1]] == "Host Details")
    if (length(host_row) > 0) {
      df_pre <- df_pre[1:(host_row - 1), ]
    }
    
    # if trimming removes all relevant lines, set to empty tibble
    if (nrow(df_pre) == 0) return(tibble())
    
    # reconstruct the relevant lines as CSV strings
    # only keep rows 3 and 4
    if (month %in% c("0125", "0225", "0324")) {
      pre_lines <- df_pre[3:4, ] %>%
        unite("line", everything(), sep = "\t") %>%
        pull(line)
      
      # reconvert the lines to a TSV
      clean_df_pre <- read_tsv(I(pre_lines), col_names = TRUE)
    } else {
      pre_lines <- df_pre[3:4, ] %>%
        unite("line", everything(), sep = ",") %>%
        pull(line)
      
      # reconvert the lines to a CSV
      clean_df_pre <- read_csv(I(pre_lines), col_names = TRUE)
    }
    
    # add report_generated_time column (from one of the trimmed rows)
    report_time <- df_pre[2, 2] %>% as.character()
    
    clean_df_pre <- clean_df_pre %>% 
      mutate(report_generated_time = report_time) %>%
      # rename columns in usable formats
      rename_with(~ gsub(" ", "_", tolower(.x))) %>%
      rename(
        actual_duration_m     = `actual_duration_(minutes)`,
        registrants           = any_of(c("#_registrants", "#_registered")),
        cancelled_registrants = any_of(c("#_cancelled_registrants", "#_cancelled"))) %>%
      # clean up values and value classes
      mutate(
        # # not all datetime objects look consistently formatted, probably will need to verify and clean later
        # # ex. AM/PM (%p) not always specified? Seconds (%S) not always specified
        # across(contains("_time"), ~ as.POSIXct(.x, format = "%b %d, %Y %H:%M")),
        across(c(actual_duration_m, registrants, cancelled_registrants, unique_viewers, total_users, max_concurrent_views), ~ as.numeric(.x)),
        enable_registration = ifelse(enable_registration == "Yes", T, F)) %>%
      select(where(~ !all(is.na(.x))))
  }
  
  return(list(pre_marker = clean_df_pre, post_marker = clean_df_post))
  
}

## wrap read_webinar_csv() function to print errors and not stop run ----
safe_read_webinar_csv <- function(lines, file_name, month) {
  tryCatch(
    {
      read_webinar_csv(lines, month)
    },
    error = function(e) {
      message("Failed for file: ", month, ", ", file_name)
      message("Error message: ", e$message)
      tibble()
    }
  )
}

# testing on one webinar file
lines <- get_test_list[["0225"]]
month <- "0225"
read_test <- read_webinar_csv(lines, month)

## process all webinar files in webinar_filenames ----
webinars_list <- pmap(
  list(
    file_name = webinar_filenames$file_name,
    file_id = webinar_filenames$file_id,
    mime_type = webinar_filenames$mime_type,
    month = webinar_filenames$month
  ),
  function(file_name, file_id, mime_type, month) {
    lines <- get_webinar_text(file_name, file_id, mime_type, month)
    safe_read_webinar_csv(lines, file_name, month)
  }
) |> 
  set_names(webinar_filenames$month)


# name list by month (not necessary if including set_names() in the pmap())
names(webinars_list) <- webinar_filenames$month

### manual fix for messy/bungled original file ----
# 0225 df: pre-marker dates were warped in the read_sheet() --> readLines()
webinars_list$`0225`$pre_marker <- webinars_list$`0225`$pre_marker %>%
  # remove unwanted columns (example: remove all-NA columns)
  select(-contains("null")) %>%
  # assign a new value to a specific cell
  mutate(actual_start_time = replace(actual_start_time, 1, "Feb 10, 2025 10:42 AM"),
         report_generated_time = replace(report_generated_time, 1, "Feb 10, 2025 2:35 PM"))

# create master webinar df ----
webinars_long <- map_dfr(
  names(webinars_list),
  ~ mutate(webinars_list[[.x]]$pre_marker, month = .x)
)

# create master attendee df ----
attendees_long <- map_dfr(
  names(webinars_list),
  ~ mutate(webinars_list[[.x]]$post_marker, month = .x)
)
# 8405 attendees (not deduplicated)

unique_attendees <- attendees_long %>% distinct(email, .keep_all = TRUE)
# 5101 unique attendees

attended_attendees <- attendees_long %>% filter(attended) %>% distinct(email, .keep_all = TRUE)
# 2142 unique attendees who actually attended

# remove attendees who were logged multiple times in the same month/session
attendees_acrossmonths <- attendees_long %>%
  group_by(email, month) %>%
  slice_max(time_in_session_m, n = 1, with_ties = FALSE) %>%
  ungroup()

# how many email addresses recur?
is_dup <- duplicated(attendees_acrossmonths$email) | duplicated(attendees_acrossmonths$email, fromLast = TRUE)
overlaps <- attendees_acrossmonths[is_dup, ]
unique_overlaps <- overlaps %>% distinct(email, .keep_all = TRUE)
# 1081 unique repeat attendees (could also be no-shows in earlier webinars)
# 5101 (overall attendees) - 1081 (repeat attendees) = 4020 (one-time attendees)

# how many of these people actually attended? 
attended_overlaps <- overlaps %>% filter(attended)
# 889 repeat attendees who actually attended

unique_attended_overlaps <- attended_overlaps %>% distinct(email, .keep_all = TRUE)
# 554 unique repeat attendees who actually attended
# 2142 (overall attended attendees) - 554 (repeat attended attendees) = 1588 (one-time attended attendees)

# need to clean up dates if doing any analyses with dates
# # not all datetime objects look consistently formatted, probably will need to verify and clean later
# # ex. AM/PM (%p) not always specified? Seconds (%S) not always specified