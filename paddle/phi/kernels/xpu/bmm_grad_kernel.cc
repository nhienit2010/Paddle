// Copyright (c) 2022 PaddlePaddle Authors. All Rights Reserved.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

#include "paddle/phi/kernels/bmm_grad_kernel.h"

#include "paddle/phi/kernels/xpu/bmm_xpu_utils.h"

namespace phi {

template <typename T, typename Context>
void MatMul(const Context& dev_ctx,
            const DenseTensor& a,
            bool trans_a,
            const DenseTensor& b,
            bool trans_b,
            DenseTensor* out) {
  using XPUT = typename XPUTypeTrait<T>::Type;
  dev_ctx.template Alloc<T>(out);
  xpu::Context* xpu_ctx = dev_ctx.x_context();
  int fccal_type = FCCalcType<XPUT>();
  if (fccal_type == XPUFCCalcType::FC_INT32) {
    MatMulXPUFunction<T, int32_t>(a, b, out, trans_a, trans_b, xpu_ctx);
  } else if (fccal_type == XPUFCCalcType::FC_FLOAT) {
    MatMulXPUFunction<T, float>(a, b, out, trans_a, trans_b, xpu_ctx);
  } else if (fccal_type == XPUFCCalcType::FC_INT32_WITH_LL) {
    MatMulXPUFunction<T, int_with_ll_t>(a, b, out, trans_a, trans_b, xpu_ctx);
  } else if (fccal_type == XPUFCCalcType::FC_FLOAT16) {
    MatMulXPUFunction<T, float16>(a, b, out, trans_a, trans_b, xpu_ctx);
  } else {
    MatMulXPUFunction<T, int16_t>(a, b, out, trans_a, trans_b, xpu_ctx);
  }
}

template <typename T, typename Context>
void CalcInputGrad(const Context& dev_ctx,
                   const DenseTensor& a,
                   bool trans_a,
                   const DenseTensor& b,
                   bool trans_b,
                   DenseTensor* out) {
  if (out == nullptr) return;
  MatMul<T, Context>(dev_ctx, a, trans_a, b, trans_b, out);
}

template <typename T, typename Context>
void BmmGradKernel(const Context& dev_ctx,
                   const DenseTensor& x,
                   const DenseTensor& y,
                   const DenseTensor& out_grad,
                   DenseTensor* x_grad,
                   DenseTensor* y_grad) {
  DenseTensor x_help = x;
  DenseTensor y_help = y;
  DenseTensor out_grad_help = out_grad;
  ReshapeXYOutIntoMatrixSequence(
      &x_help, &y_help, &out_grad_help, false, false);

  phi::DDim dx_dims;
  if (x_grad) {
    dx_dims = x_grad->dims();
    if (dx_dims != x_help.dims()) {
      x_grad->Resize(x_help.dims());
    }
  }

  phi::DDim dy_dims;
  if (y_grad) {
    dy_dims = y_grad->dims();
    if (dy_dims != y_help.dims()) {
      y_grad->Resize(y_help.dims());
    }
  }

  CalcInputGrad<T, Context>(
      dev_ctx, out_grad_help, false, y_help, true, x_grad);
  CalcInputGrad<T, Context>(
      dev_ctx, x_help, true, out_grad_help, false, y_grad);

  if (x_grad) {
    if (dx_dims != x_help.dims()) {
      x_grad->Resize(dx_dims);
    }
  }
  if (y_grad) {
    if (dy_dims != y_help.dims()) {
      y_grad->Resize(dy_dims);
    }
  }
}

}  // namespace phi

PD_REGISTER_KERNEL(
    bmm_grad, XPU, ALL_LAYOUT, phi::BmmGradKernel, float, phi::dtype::float16) {
}
