library(jsonlite)
library(dplyr)
library(tidyr)
library(purrr)

# help desk conversations
conversations <- fromJSON(
  "~Desktop/helpscout_conversations_0825.json",
  flatten = TRUE
)

# count how many messages in the thread were from the customer vs from the desk
# two new columns: customer_threads, desk_threads
conversations <- conversations %>%
  mutate(
    customer_threads = map_int(
      threads,
      ~ sum(.x$type == "customer", na.rm = TRUE)
    ),
    desk_threads = map_int(
      threads,
      ~ sum(.x$type == "message", na.rm = TRUE)
    )
  ) %>%
  # convert tags list to character vector
  mutate(
    tags = purrr::map_chr(
      tags,
      ~ if (length(.x) == 0) NA_character_ else paste(.x, collapse = "; ")
    )
  )

custom_fields_wide <- conversations %>%
  select(id, customFields) %>%
  unnest_longer(customFields) %>%
  unnest_wider(customFields) %>%
  pivot_wider(
    names_from = name,
    values_from = text
  )

conversations_wide <- conversations %>%
  select(-customFields) %>%
  left_join(custom_fields_wide, by = "id")

# get first week (8/9-8/15)
conversations_wide_wk <- conversations_wide %>%
  mutate(createdAt = as.POSIXct(createdAt, tz = "UTC")) %>%
  filter(createdAt >= as.POSIXct("2026-08-09 00:00:00", tz = "UTC"),
         createdAt < as.POSIXct("2026-08-16 00:00:00", tz = "UTC"))

# by Attitude towards OSF ----
attitude_levels = c("Positive", "Neutral", "Negative")

attitude_conversations <- conversations_wide_wk %>%
  mutate(`Attitude towards OSF` = factor(`Attitude towards OSF`, levels = attitude_levels)) %>%
  group_by(`Attitude towards OSF`) %>%
  summarise(total_count = n(),
            transition_count = sum(`OSF Transition` == "OSF Transition", na.rm = TRUE),
            transition_percent = round(transition_count / total_count * 100, 2),
            .groups = "drop"
  ) %>%
  arrange(`Attitude towards OSF`)

attitude_conv_long <- attitude_conversations %>%
  pivot_longer(
    cols = c(total_count, transition_count, transition_percent),
    names_to = "measure",
    values_to = "value"
  ) %>%
  rename(attitude = `Attitude towards OSF`)

# by Product ----
product_levels = c("Account/Profiles", "API/Integrations", "External Preprint Providers", "Global (All of OSF)", "Institutions", "Preprints", "Projects", "Registrations", "Support/Help Center", "Other", "N/A")

product_conversations <- conversations_wide_wk %>%
  mutate(Product = case_when(Product == "API/ Integrations" ~ "API/Integrations",
                             Product == "Support/ Help Center" ~ "Support/Help Center",
                             Product == "N/a" ~ "N/A",
                             .default = Product)) %>%
  mutate(Product = factor(Product, levels = product_levels)) %>%
  group_by(Product) %>%
  summarise(total_count = n(),
            transition_count = sum(`OSF Transition` == "OSF Transition", na.rm = TRUE),
            transition_percent = round(transition_count / total_count * 100, 2),
            .groups = "drop"
  ) %>%
  arrange(Product)

product_conv_long <- product_conversations %>%
  pivot_longer(
    cols = c(total_count, transition_count, transition_percent),
    names_to = "measure",
    values_to = "value"
  ) %>%
  rename(product = Product)

# by Main Themes ----
mtheme_levels = c("Collaboration Research Community and Moderation", "Onboarding Guidance and Resources", "Technical Failures (Bugs and Limitations)", "User Experience Navigation and Workflow Challenges", "Other", "N/A")

mtheme_conversations <- conversations_wide_wk %>%
  mutate(`Main Themes` = factor(`Main Themes`, levels = mtheme_levels)) %>%
  group_by(`Main Themes`) %>%
  summarise(total_count = n(),
            transition_count = sum(`OSF Transition` == "OSF Transition", na.rm = TRUE),
            transition_percent = round(transition_count / total_count * 100, 2),
            .groups = "drop"
  ) %>%
  arrange(`Main Themes`)

mtheme_conv_long <- mtheme_conversations %>%
  pivot_longer(
    cols = c(total_count, transition_count, transition_percent),
    names_to = "measure",
    values_to = "value"
  ) %>%
  rename(main_theme = `Main Themes`)