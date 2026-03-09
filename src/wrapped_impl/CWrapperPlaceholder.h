#pragma once

namespace EvalAndVizGears_for_ComputerVision
{
class CWrapperPlaceholder
{
  public:
    CWrapperPlaceholder() = default;

    double getDataMember() const;
    void setDataMember(double value);

    static double multiplyBy2(double value);

  private:
    double a_float_number_{0.0};
};

} // namespace EvalAndVizGears_for_ComputerVision
