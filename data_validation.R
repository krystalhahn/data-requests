# to validate that two datasets are identical
# before using, ensure that only common columns are included
# key_col = identifiable common column

# example usage
compare_dfs(inst_metrics, inst_metrics_parameterized, "institution.name")

compare_dfs <- function(df1, df2, key_col, verbose = TRUE, return_result = FALSE) {
  # ensure consistent row order
  if (!is.null(key_col) && key_col %in% names(df1) && key_col %in% names(df2)) {
    df2 <- df2[match(df1[[key_col]], df2[[key_col]]), ]
  }
  
  # check column names (matters if columns were added or removed)
  if (!identical(names(df1), names(df2))) {
    if (verbose) message("Column names differ — aligning df1 to df2")
    common_cols <- intersect(names(df2), names(df1))
    df1 <- df1[common_cols]
    df2 <- df2[common_cols]
  }
  
  # identify numeric and non-numeric columns
  num_cols_logical <- sapply(df1, is.numeric)
  num_cols <- which(num_cols_logical)
  non_num_cols <- names(df1)[!num_cols_logical]
  
  # find numeric columns with differences (if any)
  if (length(num_cols) > 0) {
    differing_numeric <- names(df1)[num_cols][
      sapply(names(df1)[num_cols], function(col) {
        !isTRUE(all.equal(df1[[col]], df2[[col]]))
      })
    ]
    
    # check numeric identity
    numeric_identical <- all(
      sapply(names(df1)[num_cols], function(col) {
        identical(as.numeric(df1[[col]]), as.numeric(df2[[col]]))
      })
    )
  } else {
    differing_numeric <- character(0)
    numeric_identical <- TRUE
  }
  
  # find non-numeric columns with differences
  differing_non_numeric <- non_num_cols[
    sapply(non_num_cols, function(col) {
      !isTRUE(all.equal(df1[[col]], df2[[col]], check.attributes = FALSE))
    })
  ]
  
  # check full data equality ignoring attributes
  data_equal <- isTRUE(all.equal(df1, df2, check.attributes = FALSE))
  
  # optional reporting
  if (verbose) {
    if (length(differing_numeric) == 0) {
      message("✓ All numeric columns match exactly")
    } else {
      message("✗ Numeric differences found in columns:")
      print(differing_numeric)
    }
    
    if (length(differing_non_numeric) == 0) {
      message("✓ All non-numeric columns match exactly")
    } else {
      message("✗ Non-numeric differences found in columns:")
      print(differing_non_numeric)
    }
    
    message("Data equal (ignoring attributes): ", data_equal)
    message("Numeric identity (strict): ", numeric_identical)
  }
  
  # optional structured result (mainly for unequal dfs)
  if (return_result) {
    return(list(
      data_equal = data_equal,
      numeric_identical = numeric_identical,
      differing_numeric_columns = differing_numeric,
      differing_non_numeric_columns = differing_non_numeric
    ))
  } else {
    invisible(NULL)
  }
}
