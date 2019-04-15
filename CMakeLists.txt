cmake_minimum_required(VERSION 2.8.3)
project(logger)

add_compile_options(-std=c++17)

find_package(Eigen3 REQUIRED)

include_directories(
  include
  ${Eigen3_INCLUDE_DIRS}
)

add_executable(example examples/example.cpp)
