load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")

EIGEN_TAG = "3.4.0"
EIGEN_SHA = "1ccaabbfe870f60af3d6a519c53e09f3dcf630207321dffa553564a8e75c4fc8"
http_archive(
    name = "eigen3",
    build_file_content = """
cc_library(
    name = 'eigen3',
    includes = ['.'],
    hdrs = glob(['Eigen/**']),
    visibility = ['//visibility:public'],
)
""",
    sha256 = EIGEN_SHA,
    strip_prefix = "eigen-{}".format(EIGEN_TAG),
    urls = ["https://gitlab.com/libeigen/eigen/-/archive/{0}/eigen-{0}.zip".format(EIGEN_TAG)],
)
