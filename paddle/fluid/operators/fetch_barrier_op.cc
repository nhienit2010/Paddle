/* Copyright (c) 2016 PaddlePaddle Authors. All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License. */

#include <future>  // NOLINT
#include <ostream>

#include "paddle/fluid/framework/data_type.h"
#include "paddle/fluid/framework/framework.pb.h"
#include "paddle/fluid/framework/lod_tensor.h"
#include "paddle/fluid/framework/op_registry.h"

#include "paddle/fluid/operators/detail/grpc_client.h"
#include "paddle/fluid/platform/profiler.h"

namespace paddle {
namespace operators {

class FetchBarrierOp : public framework::OperatorBase {
 public:
  FetchBarrierOp(const std::string& type,
                 const framework::VariableNameMap& inputs,
                 const framework::VariableNameMap& outputs,
                 const framework::AttributeMap& attrs)
      : OperatorBase(type, inputs, outputs, attrs) {}

  void RunImpl(const framework::Scope& scope,
               const platform::Place& place) const override {
    std::vector<std::string> eps = Attr<std::vector<std::string>>("endpoints");

    platform::DeviceContextPool& pool = platform::DeviceContextPool::Instance();
    auto& ctx = *pool.Get(place);
    // For profiling
    platform::RecordEvent record_event(Type(), &ctx);

    auto client_var_name = Output("RPCClient");
    PADDLE_ENFORCE_NOT_NULL(scope.FindVar(client_var_name),
                            "Can not find variable '%s' in the scope.",
                            client_var_name);
    auto* client_var = scope.FindVar(client_var_name);
    detail::RPCClient* rpc_client = client_var->GetMutable<detail::RPCClient>();

    PADDLE_ENFORCE(rpc_client->Wait());

    for (auto& ep : eps) {
      VLOG(3) << "fetch barrier, ep: " << ep;
      rpc_client->AsyncSendFetchBarrier(ep);
    }
    PADDLE_ENFORCE(rpc_client->Wait());
  }
};

class FetchBarrierOpMaker : public framework::OpProtoAndCheckerMaker {
 public:
  void Make() {
    AddOutput("RPCClient",
              "(RPCClient) The RPC client object which is"
              "initialized at most once.");
    AddComment(R"DOC(
SendBarrier operator

This operator will send a send barrier signal to list_and_serv op, so that
the Parameter Server would knew all variables have been sent.
)DOC");

    AddAttr<std::vector<std::string>>("endpoints",
                                      "(string vector, default 127.0.0.1:6164)"
                                      "Server endpoints to send variables to.")
        .SetDefault({"127.0.0.1:6164"});
  }
};

class FetchBarrierOpVarTypeInference : public framework::VarTypeInference {
 public:
  void operator()(const framework::OpDesc& op_desc,
                  framework::BlockDesc* block) const override {
    auto out_var_name = op_desc.Output("RPCClient").front();
    auto& out_var = block->FindRecursiveOrCreateVar(out_var_name);
    auto var_type = framework::proto::VarType::RAW;
    out_var.SetType(var_type);
  }
};

class FetchBarrierOpShapeInference : public framework::InferShapeBase {
 public:
  void operator()(framework::InferShapeContext* ctx) const override {}
};

}  // namespace operators
}  // namespace paddle

namespace ops = paddle::operators;

REGISTER_OPERATOR(fetch_barrier, ops::FetchBarrierOp,
                  paddle::framework::EmptyGradOpMaker, ops::FetchBarrierOpMaker,
                  ops::FetchBarrierOpVarTypeInference,
                  ops::FetchBarrierOpShapeInference);
