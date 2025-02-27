paddle_test(symbol_dim_expr_test SRCS symbol_dim_expr_test.cc)
paddle_test(simplify_dim_expr_test SRCS simplify_dim_expr_test.cc)

if(WITH_CINN)
  paddle_test(shape_analysis_test SRCS shape_analysis_test.cc)
  set_tests_properties(
    shape_analysis_test PROPERTIES ENVIRONMENT
                                   "FLAGS_enable_pir_in_executor=true")

  paddle_test(shape_optimization_test SRCS shape_optimization_test.cc)
  set_tests_properties(
    shape_optimization_test PROPERTIES ENVIRONMENT
                                       "FLAGS_enable_pir_in_executor=true")

  paddle_test(infer_symbolic_shape_test SRCS infer_symbolic_shape_test.cc)
  set_tests_properties(
    infer_symbolic_shape_test PROPERTIES ENVIRONMENT
                                         "FLAGS_enable_pir_in_executor=true")
endif()

if(WITH_ONNXRUNTIME AND WIN32)
  # Copy onnxruntime for some c++ test in Windows, since the test will
  # be build only in CI, so suppose the generator in Windows is Ninja.
  copy_onnx(symbol_dim_expr_test)
endif()
