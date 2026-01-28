merge_nps_users_insts <- function(nps_users_path, nps_insts_path, ...) {
  aggregated_insts <- readr::read_csv(nps_insts_path, ...) |>
    dplyr::group_by(u._id) |>
    dplyr::summarize(
      institutions = paste(unique(institution_name), collapse = ", ")
    )

  readr::read_csv(nps_users_path, ...) |>
    dplyr::left_join(aggregated_insts, by = "u._id") |>
    dplyr::select(
      u._id,
      u.username,
      u.date_confirmed,
      u.date_last_login,
      u.date_last_action,
      institutions,
      dplyr::everything()
    )
}


classify_users <- function(nps_data, cutoff_date) {
  nps_data |>
    subset(u.date_confirmed < cutoff_date) |>
    dplyr::rowwise() |>
    dplyr::mutate(
      los_project = ifelse(public_projects_created > 0, T, F),
      los_registration = ifelse(
        public_registrations_created > 0 | embargoed_registrations_created > 0,
        T,
        F
      ),
      los_preprint = ifelse(published_preprints_created > 0, T, F)
    ) |>
    dplyr::mutate(
      user_type = dplyr::case_when(
        sum(los_project, los_registration, los_preprint) == 3 ~ "champion",
        sum(los_project, los_registration, los_preprint) == 2 ~ "active",
        sum(los_project, los_registration, los_preprint) == 1 ~ "emerging",
        TRUE ~ "novice"
      ),
      is_institutional = !is.na(institutions) & institutions != ""
    ) |>
    dplyr::group_by(user_type) |>
    dplyr::summarise(
      user_count = dplyr::n(),
      inst_user_count = sum(is_institutional, na.rm = TRUE)
    )
}
