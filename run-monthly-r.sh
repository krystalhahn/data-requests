#!/bin/bash

# Set variables for NPS data processing
NPS_CSV=/tmp/nps_users.csv
NPS_INSTS_CSV=/tmp/nps_users_insts.csv
NPS_CUTOFF_DATE=2026-01-01


./monthly/munge-nps.r \
    $NPS_CSV \
    $NPS_INSTS_CSV \
    $NPS_CUTOFF_DATE \