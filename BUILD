load("@rules_cc//cc:defs.bzl", "cc_library")

cc_library(
    name = "tidal",
    hdrs = ["include/tidal/tidal.h"],
    strip_include_prefix = "include",
    visibility = ["//visibility:public"],
    deps = ["@eigen"],
)
