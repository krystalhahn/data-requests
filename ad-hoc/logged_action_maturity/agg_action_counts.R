# read in output from all_actions.py
## update file path
logged_actions <- read_csv('~/Desktop/all_actions.csv')

# get years based on users' date of confirmation
logged_actions_years <- logged_actions %>%
  mutate(year_confirmed = year(user_confirmed))

# this is a version of the code that is more precise than previous iterations
## calculates months more precisely (365/12 days vs 30 or 30.42)
logged_action_aggmeans <- logged_actions_years %>%
  mutate(age_at_action = action_created - user_confirmed) %>%
  mutate(user_maturity = case_when(age_at_action < ddays(1) ~ '1_day',
                                   (age_at_action >= ddays(1)) & (age_at_action < ddays(7)) ~ '1_week',
                                   (age_at_action >= ddays(7)) & (age_at_action < dmonths(1)) ~ '1_month',
                                   (age_at_action >= dmonths(1)) & (age_at_action < dmonths(3)) ~ '3_months',
                                   (age_at_action >= dmonths(3)) & (age_at_action < dmonths(6)) ~ '6_months',
                                   (age_at_action >= dmonths(6)) & (age_at_action < dyears(1)) ~ '1_year',
                                   (age_at_action >= dyears(1)) & (age_at_action < dyears(2)) ~ '2_years',
                                   (age_at_action >= dyears(2)) & (age_at_action < dyears(3)) ~ '3_years',
                                   (age_at_action >= dyears(3)) & (age_at_action < dyears(5)) ~ '5_years',
                                   age_at_action >= dyears(5) ~ 'after_5_years')) %>%
  # count how many actions for each year and user_maturity category
  summarize(agg_action_count = n(),
            # count how many users did each action in each year and user_maturity category
            unique_users = n_distinct(user_id)) %>%
  # calculate the mean count for each action in each year and user_maturity category using the action count and user count
  mutate(mean_action_count = round(agg_action_count / unique_users, 2)) %>%
  ungroup() 

# how many of these users with logged actions were confirmed in each year?
users_years <- logged_actions_years %>%
  select(user_id, year_confirmed) %>%
  distinct(user_id) %>%
  group_by(year_confirmed) %>%
  summarize(user_count = n())