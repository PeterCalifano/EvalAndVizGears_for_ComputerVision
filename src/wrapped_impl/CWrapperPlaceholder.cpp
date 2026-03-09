#include "CWrapperPlaceholder.h"

namespace EvalAndVizGears_for_ComputerVision
{

double CWrapperPlaceholder::getDataMember() const
{
  return a_float_number_;
}

void CWrapperPlaceholder::setDataMember(double value)
{
  a_float_number_ = value;
}

double CWrapperPlaceholder::multiplyBy2(double value)
{
  return value * 2.0;
}

} // namespace EvalAndVizGears_for_ComputerVision
