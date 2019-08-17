#include <logger/logger.h>

#include <eigen3/Eigen/Core>

#include<random>

int main()
{
  logger::Logger log("/tmp/ramdisk/stress.bin");

  auto scalar_stream = log.add_scalar_stream<double, float, uint64_t, int>("Scalar");
  auto vector_stream = log.add_vector_stream<double, 12>("Vector");
  auto matrix_stream = log.add_matrix_stream<double, 9, 9>("Matrix");

  std::random_device rd;
  std::mt19937 gen(rd());
  std::uniform_int_distribution<uint64_t> uint_dis;
  std::uniform_int_distribution<int> int_dis;
  std::uniform_real_distribution<float> float_dis;
  std::uniform_real_distribution<double> double_dis;

  size_t num_iterations = 1000000;

  for (size_t i = 0; i < num_iterations; i++)
  {
    scalar_stream.log(i, double_dis(gen), float_dis(gen), uint_dis(gen), int_dis(gen));
    vector_stream.log(i, Eigen::Matrix<double, 12, 1>::Random());
    matrix_stream.log(i, Eigen::Matrix<double, 9, 9>::Random());
  }
}