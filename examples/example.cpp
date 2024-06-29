#include <tidal/tidal.h>

#include <Eigen/Core>

int main()
{
  tidal::Log log("meh.bin");

  auto scalar_stream = log.add_scalar_stream<int, float, double, bool>("Scalar Stream");
  auto vector_stream = log.add_vector_stream<uint8_t, 6>("Vector Stream");

  scalar_stream->set_labels("alpha", "bravo", "charlie", "delta");

  scalar_stream->log(4000, 4298, 8.350f, 654.23, true);

  Eigen::Matrix<uint8_t, 6, 1> vector_data = Eigen::Matrix<uint8_t, 6, 1>::LinSpaced(4, 10);
  vector_stream->log(4001, vector_data);

  auto matrix_stream = log.add_matrix_stream<float, 3, 3>("Matrix Stream");

  Eigen::Matrix<float, 3, 3> matrix_data = Eigen::Matrix<float, 3, 3>::Identity();
  matrix_stream->log(4002, matrix_data);

  return 0;
}
