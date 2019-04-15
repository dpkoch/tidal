#ifndef LOGGER_LOGGER_H
#define LOGGER_LOGGER_H

#include <cstdint>
#include <fstream>
#include <string>
#include <type_traits>

// #include <utility>
#include <iostream>

#include <eigen3/Eigen/Core>

namespace logger
{


// The log file will have a header that looks like the following:
//   logger version?
//   timestamp?
//   number of streams
//   List of streams:
//     ID (u8) | Name (null-terminated string) | type specifier (see below)

// allow for the following types specifiers:
//  * data type | specifier (type)
//  * scalar | scalar (u8) number (u32) [type (u8) ...]
//  * vector | vector (u8) type (u8) elements (u32)
//  * matrix (row-major?) | matrix (u8) type (u8) rows (u32) cols (u32)

enum class DataClass : uint8_t
{
  SCALAR,
  VECTOR,
  MATRIX
};

enum class ScalarType : uint8_t
{
  u8,
  i8,
  u16,
  i16,
  u32,
  i32,
  u64,
  i64,
  f32,
  f64
};

template <typename T> ScalarType resolve_scalar_type() = delete;
template <> ScalarType resolve_scalar_type<uint8_t>()  { return ScalarType::u8; }
template <> ScalarType resolve_scalar_type<int8_t>()   { return ScalarType::i8; }
template <> ScalarType resolve_scalar_type<uint16_t>() { return ScalarType::u16; }
template <> ScalarType resolve_scalar_type<int16_t>()  { return ScalarType::i16; }
template <> ScalarType resolve_scalar_type<uint32_t>() { return ScalarType::u32; }
template <> ScalarType resolve_scalar_type<int32_t>()  { return ScalarType::i32; }
template <> ScalarType resolve_scalar_type<uint64_t>() { return ScalarType::u64; }
template <> ScalarType resolve_scalar_type<int64_t>()  { return ScalarType::i64; }
template <> ScalarType resolve_scalar_type<float>()    { return ScalarType::f32; }
template <> ScalarType resolve_scalar_type<double>()   { return ScalarType::f64; }

class Logger
{
public:

  class Stream
  {
  public:
    Stream(Logger &logger, unsigned int id) :
      logger_(logger),
      id_(id)
    {}
    virtual ~Stream() {}

    void write_header(const std::string& name)
    {
      // write header
      logger_ << Logger::HEADER_MARKER << id_ << name;
      write_format();
    }

    unsigned int id() const { return id_; }

  protected:
    Logger &logger_;
    unsigned int id_;

    virtual void write_format() = 0;

    inline void write_data_prefix(unsigned long timestamp)
    {
      logger_ << Logger::DATA_MARKER << id_ << timestamp;
    }
  };

  template <typename... Ts>
  class ScalarStream : public Stream
  {
  public:
    ScalarStream(Logger &logger, unsigned int id) : Stream(logger, id) {}

    void write_format() override
    {
      logger_ << DataClass::SCALAR << static_cast<uint32_t>(sizeof...(Ts));
      format_recurse<Ts...>();
    }

    void log(unsigned long timestamp, Ts... data)
    {
      write_data_prefix(timestamp);
      log_recurse(data...);
    }

  private:
    template <typename First, typename... Tail>
    void log_recurse(First value, Tail... tail)
    {
      logger_ << value;
      log_recurse(tail...);
    }

    template <typename... Tail>
    void log_recurse(Tail... tail) {}

    template <typename First, typename... Tail>
    void format_recurse()
    {
      logger_ << resolve_scalar_type<First>();
      format_recurse<Tail...>();
    }

    template <typename... Tail>
    typename std::enable_if<sizeof...(Tail) == 0>::type format_recurse() {}
  };

  template <typename T, unsigned int elements>
  class VectorStream : public Stream
  {
  public:
    VectorStream(Logger &logger, unsigned int id) : Stream(logger, id) {}

    void write_format() override
    {
      logger_ << DataClass::VECTOR << resolve_scalar_type<T>() << elements;
    }

    void log(unsigned long timestamp, const Eigen::Matrix<T, elements, 1> &data)
    {
      write_data_prefix(timestamp);
      logger_ << data;
    }
  };

  template <typename T, unsigned int rows, unsigned int cols>
  class MatrixStream : public Stream
  {
  public:
    MatrixStream(Logger &logger, unsigned int id) : Stream(logger, id) {}

    void write_format() override
    {
      logger_ << DataClass::MATRIX << resolve_scalar_type<T>() << rows << cols;
    }

    void log(unsigned long timestamp, const Eigen::Matrix<T, rows, cols> &data)
    {
      write_data_prefix(timestamp);
      logger_ << data;
    }
  };

  Logger(const std::string& filename) : file_(filename, std::ios_base::out | std::ios_base::binary) {}
  ~Logger() { file_.close(); }

  // setup up the log file
  // have the following 3 functions either do nothing or throw an exception if called after any of the log_* functions?
  // also need to check for duplicate string names
  //
  // maybe these guys could return some object that you use to log, which could enforce that subsequent calls are of the right type?
  // So the use case would look something like
  //     Logger logger(file);
  //     auto stream1 = logger.add_scalar_stream<int, double, double>("stream1");
  //     auto stream2 = logger.add_vector_stream<double, 6>("stream2");
  //     auto stream3 = logger.add_matrix_stream<double, 3, 3>("stream3");
  //
  //     stream1.log(t, 6, 23.4, 34.12);

  // TODO add check that the stream has actually been added via one of these functions (not just created on its own)

  template <typename... Ts>
  ScalarStream<Ts...> add_scalar_stream(const std::string& name)
  {
    ScalarStream<Ts...> stream_object(*this, next_id_++);
    stream_object.write_header(name);
    // TODO add to list of approved streams?
    return stream_object;
  }

  template <typename T, unsigned int elements>
  VectorStream<T, elements> add_vector_stream(const std::string& name)
  {
    VectorStream<T, elements> stream_object(*this, next_id_++);
    stream_object.write_header(name);
    // TODO add to list of approved streams?
    return stream_object;
  }

  template <typename T, unsigned int rows, unsigned int cols>
  MatrixStream<T, rows, cols> add_matrix_stream(const std::string& name)
  {
    MatrixStream<T, rows, cols> stream_object(*this, next_id_++);
    stream_object.write_header(name);
    // TODO add to list of approved streams?
    return stream_object;
  }

  // template <typename DerivedStream, typename... Args>
  // DerivedStream add_custom_stream(const std::string& stream, Args&&... args)
  // {
  //   static_assert(std::is_base_of<Stream, DerivedStream>::value,
  //     "Type parameter DerivedStream must inherit from Stream");

  //   DerivedStream stream_object(*this, stream, std::forward<Args>(args)...);
  //   stream_object.write_header(name);
  //   // TODO add to list of approved streams?
  //   return stream_object;
  // }

private:
  static constexpr uint8_t HEADER_MARKER = 0xA5;
  static constexpr uint8_t DATA_MARKER = 0xDB;

  std::ofstream file_;
  unsigned int next_id_ = 0;

  Logger& operator<<(const std::string& data)
  {
    file_.write(data.c_str(), sizeof(char) * data.size());
    file_ << '\0'; // null terminate strings
    return *this;
  }

  template<typename T, unsigned int rows, unsigned int cols>
  Logger& operator<<(const Eigen::Matrix<T, rows, cols>& data)
  {
    file_.write(data.data(), data.size());
    return *this;
  }

  template <typename T>
  Logger& operator<<(const T& data)
  {
    file_.write(reinterpret_cast<const char*>(&data), sizeof(T));
    return *this;
  }

  friend class Stream;
};

} // namespace logger

#endif // LOGGER_LOGGER_H
