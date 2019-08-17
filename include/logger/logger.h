#ifndef LOGGER_LOGGER_H
#define LOGGER_LOGGER_H

#include <cstdint>
#include <fstream>
#include <string>
#include <type_traits>

#include <eigen3/Eigen/Core>

namespace logger
{

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
  f64,
  boolean
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
template <> ScalarType resolve_scalar_type<bool>()     { return ScalarType::boolean; }

class Logger
{
public:

  class Stream
  {
  protected:
    friend class Logger;

    Stream(Logger &logger, unsigned int id) :
      logger_(logger),
      id_(id)
    {}
    virtual ~Stream() {}

    virtual void write_format() = 0;

    inline void write_data_prefix(unsigned long timestamp)
    {
      logger_ << Marker::DATA << id_ << timestamp;
    }

    unsigned int id() const { return id_; }

    Logger &logger_;

  private:
    void write_header(const std::string& name)
    {
      logger_ << Marker::METADATA << id_ << name;
      write_format();
    }

    unsigned int id_;
  };

  template <typename... Ts>
  class ScalarStream : public Stream
  {
  public:
    friend class Logger;

    template <typename... Labels,
              typename std::enable_if<sizeof...(Labels) == sizeof...(Ts), int>::type = 0>
    void set_labels(Labels... labels)
    {
      logger_ << Marker::LABELS << id_;
      label_recurse(labels...);
    }

    void log(unsigned long timestamp, Ts... data)
    {
      write_data_prefix(timestamp);
      log_recurse(data...);
    }

  protected:
    ScalarStream(Logger &logger, unsigned int id) : Stream(logger, id) {}

    void write_format() override
    {
      logger_ << DataClass::SCALAR << static_cast<uint32_t>(sizeof...(Ts));
      format_recurse<Ts...>();
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

    template <typename... Labels>
    void label_recurse(const std::string& first, Labels... labels)
    {
      label_recurse(first);
      label_recurse(labels...);
    }

    void label_recurse(const std::string& label)
    {
      logger_ << label;
    }
  };

  template <typename T, unsigned int elements>
  class VectorStream : public Stream
  {
  public:
    friend class Logger;

    void log(unsigned long timestamp, const Eigen::Matrix<T, elements, 1> &data)
    {
      write_data_prefix(timestamp);
      logger_ << data;
    }

  protected:
    VectorStream(Logger &logger, unsigned int id) : Stream(logger, id) {}

    void write_format() override
    {
      logger_ << DataClass::VECTOR << resolve_scalar_type<T>() << elements;
    }
  };

  template <typename T, unsigned int rows, unsigned int cols>
  class MatrixStream : public Stream
  {
  public:
    friend class Logger;

    void log(unsigned long timestamp, const Eigen::Matrix<T, rows, cols> &data)
    {
      write_data_prefix(timestamp);
      logger_ << data;
    }

  protected:
    MatrixStream(Logger &logger, unsigned int id) : Stream(logger, id) {}

    void write_format() override
    {
      logger_ << DataClass::MATRIX << resolve_scalar_type<T>() << rows << cols;
    }
  };

  Logger(const std::string& filename) : file_(filename, std::ios_base::out | std::ios_base::binary) {}
  ~Logger() { file_.close(); }

  template <typename... Ts>
  ScalarStream<Ts...> add_scalar_stream(const std::string& name)
  {
    ScalarStream<Ts...> stream_object(*this, next_id_++);
    stream_object.write_header(name);
    return stream_object;
  }

  template <typename T, unsigned int elements>
  VectorStream<T, elements> add_vector_stream(const std::string& name)
  {
    VectorStream<T, elements> stream_object(*this, next_id_++);
    stream_object.write_header(name);
    return stream_object;
  }

  template <typename T, unsigned int rows, unsigned int cols>
  MatrixStream<T, rows, cols> add_matrix_stream(const std::string& name)
  {
    MatrixStream<T, rows, cols> stream_object(*this, next_id_++);
    stream_object.write_header(name);
    return stream_object;
  }

  template <typename DerivedStream, typename... Args>
  DerivedStream add_custom_stream(const std::string& name, Args&&... args)
  {
    static_assert(std::is_base_of<Stream, DerivedStream>::value,
      "Type parameter DerivedStream must inherit from Stream");

    DerivedStream stream_object(*this, name, std::forward<Args>(args)...);
    stream_object.write_header(name);
    return stream_object;
  }

private:
  enum class DataClass : uint8_t
  {
    SCALAR,
    VECTOR,
    MATRIX
  };

  enum class Marker : uint8_t
  {
    METADATA = 0xA5,
    LABELS = 0x66,
    DATA = 0xDB
  };

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

  std::ofstream file_;
  unsigned int next_id_ = 0;
};

} // namespace logger

#endif // LOGGER_LOGGER_H
