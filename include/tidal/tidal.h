/*
 * MIT License
 *
 * Copyright (c) 2020 Daniel Koch
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

#ifndef TIDAL_TIDAL_H
#define TIDAL_TIDAL_H

#include <cstdint>
#include <fstream>
#include <memory>
#include <string>
#include <type_traits>

#include <Eigen/Core>

namespace tidal
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

class Log
{
public:

  class Stream
  {
  protected:
    friend class Log;

    Stream(Log &log, unsigned int id) :
      log_(log),
      id_(id)
    {}
    virtual ~Stream() {}

    virtual void write_format() = 0;

    inline void write_data_prefix(unsigned long timestamp)
    {
      log_ << Marker::DATA << id_ << timestamp;
    }

    unsigned int id() const { return id_; }

    Log &log_;

  private:
    void write_header(const std::string& name)
    {
      log_ << Marker::METADATA << id_ << name;
      write_format();
    }

    unsigned int id_;
  };

  template <typename... Ts>
  class ScalarStream : public Stream
  {
  public:
    friend class Log;

    template <typename... Labels>
    typename std::enable_if<sizeof...(Labels) == sizeof...(Ts)>::type set_labels(Labels... labels)
    {
      log_ << Marker::LABELS << id_;
      label_recurse(labels...);
    }

    void log(unsigned long timestamp, Ts... data)
    {
      write_data_prefix(timestamp);
      log_recurse(data...);
    }

  protected:
    ScalarStream(Log &log, unsigned int id) : Stream(log, id) {}

    void write_format() override
    {
      log_ << DataClass::SCALAR << static_cast<uint32_t>(sizeof...(Ts));
      format_recurse<Ts...>();
    }

  private:
    template <typename First, typename... Tail>
    void log_recurse(First value, Tail... tail)
    {
      log_ << value;
      log_recurse(tail...);
    }

    template <typename... Tail>
    void log_recurse(Tail... tail) {}

    template <typename First, typename... Tail>
    void format_recurse()
    {
      log_ << resolve_scalar_type<First>();
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
      log_ << label;
    }
  };

  template <typename T, unsigned int elements>
  class VectorStream : public Stream
  {
  public:
    friend class Log;

    void log(unsigned long timestamp, const Eigen::Matrix<T, elements, 1> &data)
    {
      write_data_prefix(timestamp);
      log_ << data;
    }

  protected:
    VectorStream(Log &log, unsigned int id) : Stream(log, id) {}

    void write_format() override
    {
      log_ << DataClass::VECTOR << resolve_scalar_type<T>() << elements;
    }
  };

  template <typename T, unsigned int rows, unsigned int cols>
  class MatrixStream : public Stream
  {
  public:
    friend class Log;

    void log(unsigned long timestamp, const Eigen::Matrix<T, rows, cols> &data)
    {
      write_data_prefix(timestamp);
      log_ << data;
    }

  protected:
    MatrixStream(Log &log, unsigned int id) : Stream(log, id) {}

    void write_format() override
    {
      log_ << DataClass::MATRIX << resolve_scalar_type<T>() << rows << cols;
    }
  };

  Log(const std::string& filename) : file_(filename, std::ios_base::out | std::ios_base::binary) {}
  ~Log() { file_.close(); }

  template <typename... Ts>
  std::shared_ptr<ScalarStream<Ts...>> add_scalar_stream(const std::string& name)
  {
    std::shared_ptr<ScalarStream<Ts...>> ptr(new ScalarStream<Ts...>(*this, next_id_++));
    ptr->write_header(name);
    return ptr;
  }

  template <typename T, unsigned int elements>
  std::shared_ptr<VectorStream<T, elements>> add_vector_stream(const std::string& name)
  {
    std::shared_ptr<VectorStream<T, elements>> ptr(new VectorStream<T, elements>(*this, next_id_++));
    ptr->write_header(name);
    return ptr;
  }

  template <typename T, unsigned int rows, unsigned int cols>
  std::shared_ptr<MatrixStream<T, rows, cols>> add_matrix_stream(const std::string& name)
  {
    std::shared_ptr<MatrixStream<T, rows, cols>> ptr(new MatrixStream<T, rows, cols>(*this, next_id_++));
    ptr->write_header(name);
    return ptr;
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

  Log& operator<<(const std::string& data)
  {
    file_.write(data.c_str(), sizeof(char) * data.size());
    file_ << '\0'; // null terminate strings
    return *this;
  }

  template<typename T, unsigned int rows, unsigned int cols>
  Log& operator<<(const Eigen::Matrix<T, rows, cols>& data)
  {
    file_.write(data.data(), data.size());
    return *this;
  }

  template <typename T>
  Log& operator<<(const T& data)
  {
    file_.write(reinterpret_cast<const char*>(&data), sizeof(T));
    return *this;
  }

  std::ofstream file_;
  unsigned int next_id_ = 0;
};

} // namespace tidal

#endif // TIDAL_TIDAL_H
