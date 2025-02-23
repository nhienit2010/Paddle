# Copyright (c) 2020 PaddlePaddle Authors. All Rights Reserved.
# Copyright (c) 2020 PaddlePaddle Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import tempfile
import unittest

import numpy as np

import paddle
from paddle import base, nn


class SimpleFCLayer(nn.Layer):
    def __init__(self, feature_size, batch_size, fc_size):
        super().__init__()
        self._linear = nn.Linear(feature_size, fc_size)
        self._offset = paddle.to_tensor(
            np.random.random((batch_size, fc_size)).astype('float32')
        )

    def forward(self, x):
        fc = self._linear(x)
        return fc + self._offset


class LinearNetWithNone(nn.Layer):
    def __init__(self, feature_size, fc_size):
        super().__init__()
        self._linear = nn.Linear(feature_size, fc_size)

    def forward(self, x):
        fc = self._linear(x)

        return [fc, [None, 2]]


class TestTracedLayerErrMsg(unittest.TestCase):
    def setUp(self):
        self.batch_size = 4
        self.feature_size = 3
        self.fc_size = 2
        self.layer = self._train_simple_net()
        self.type_str = 'class'
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_trace_err(self):
        if base.framework.in_dygraph_mode():
            return
        with base.dygraph.guard():
            in_x = paddle.to_tensor(
                np.random.random((self.batch_size, self.feature_size)).astype(
                    'float32'
                )
            )

            with self.assertRaises(AssertionError) as e:
                dygraph_out, traced_layer = base.dygraph.TracedLayer.trace(
                    None, [in_x]
                )
            self.assertEqual(
                "The type of 'layer' in paddle.jit.TracedLayer.trace must be paddle.nn.Layer, but received <{} 'NoneType'>.".format(
                    self.type_str
                ),
                str(e.exception),
            )
            with self.assertRaises(TypeError) as e:
                dygraph_out, traced_layer = base.dygraph.TracedLayer.trace(
                    self.layer, 3
                )
            self.assertEqual(
                "The type of 'each element of inputs' in paddle.jit.TracedLayer.trace must be base.Variable, but received <{} 'int'>.".format(
                    self.type_str
                ),
                str(e.exception),
            )
            with self.assertRaises(TypeError) as e:
                dygraph_out, traced_layer = base.dygraph.TracedLayer.trace(
                    self.layer, [True, 1]
                )
            self.assertEqual(
                "The type of 'each element of inputs' in paddle.jit.TracedLayer.trace must be base.Variable, but received <{} 'bool'>.".format(
                    self.type_str
                ),
                str(e.exception),
            )

            dygraph_out, traced_layer = base.dygraph.TracedLayer.trace(
                self.layer, [in_x]
            )

    def test_set_strategy_err(self):
        if base.framework.in_dygraph_mode():
            return
        with base.dygraph.guard():
            in_x = paddle.to_tensor(
                np.random.random((self.batch_size, self.feature_size)).astype(
                    'float32'
                )
            )
            dygraph_out, traced_layer = base.dygraph.TracedLayer.trace(
                self.layer, [in_x]
            )

            with self.assertRaises(AssertionError) as e:
                traced_layer.set_strategy(1, base.ExecutionStrategy())
            self.assertEqual(
                "The type of 'build_strategy' in paddle.jit.TracedLayer.set_strategy must be base.BuildStrategy, but received <{} 'int'>.".format(
                    self.type_str
                ),
                str(e.exception),
            )

            with self.assertRaises(AssertionError) as e:
                traced_layer.set_strategy(base.BuildStrategy(), False)
            self.assertEqual(
                "The type of 'exec_strategy' in paddle.jit.TracedLayer.set_strategy must be base.ExecutionStrategy, but received <{} 'bool'>.".format(
                    self.type_str
                ),
                str(e.exception),
            )

            traced_layer.set_strategy(build_strategy=base.BuildStrategy())
            traced_layer.set_strategy(exec_strategy=base.ExecutionStrategy())
            traced_layer.set_strategy(
                base.BuildStrategy(), base.ExecutionStrategy()
            )

    def test_save_inference_model_err(self):
        if base.framework.in_dygraph_mode():
            return
        with base.dygraph.guard():
            in_x = paddle.to_tensor(
                np.random.random((self.batch_size, self.feature_size)).astype(
                    'float32'
                )
            )
            dygraph_out, traced_layer = base.dygraph.TracedLayer.trace(
                self.layer, [in_x]
            )

            path = os.path.join(self.temp_dir.name, './traced_layer_err_msg')
            with self.assertRaises(TypeError) as e:
                traced_layer.save_inference_model([0])
            self.assertEqual(
                "The type of 'path' in paddle.jit.TracedLayer.save_inference_model must be <{} 'str'>, but received <{} 'list'>. ".format(
                    self.type_str, self.type_str
                ),
                str(e.exception),
            )
            with self.assertRaises(TypeError) as e:
                traced_layer.save_inference_model(path, [0], [None])
            self.assertEqual(
                "The type of 'each element of fetch' in paddle.jit.TracedLayer.save_inference_model must be <{} 'int'>, but received <{} 'NoneType'>. ".format(
                    self.type_str, self.type_str
                ),
                str(e.exception),
            )
            with self.assertRaises(TypeError) as e:
                traced_layer.save_inference_model(path, [0], False)
            self.assertEqual(
                "The type of 'fetch' in paddle.jit.TracedLayer.save_inference_model must be (<{} 'NoneType'>, <{} 'list'>), but received <{} 'bool'>. ".format(
                    self.type_str, self.type_str, self.type_str
                ),
                str(e.exception),
            )
            with self.assertRaises(TypeError) as e:
                traced_layer.save_inference_model(path, [None], [0])
            self.assertEqual(
                "The type of 'each element of feed' in paddle.jit.TracedLayer.save_inference_model must be <{} 'int'>, but received <{} 'NoneType'>. ".format(
                    self.type_str, self.type_str
                ),
                str(e.exception),
            )
            with self.assertRaises(TypeError) as e:
                traced_layer.save_inference_model(path, True, [0])
            self.assertEqual(
                "The type of 'feed' in paddle.jit.TracedLayer.save_inference_model must be (<{} 'NoneType'>, <{} 'list'>), but received <{} 'bool'>. ".format(
                    self.type_str, self.type_str, self.type_str
                ),
                str(e.exception),
            )
            with self.assertRaises(ValueError) as e:
                traced_layer.save_inference_model("")
            self.assertEqual(
                "The input path MUST be format of dirname/file_prefix [dirname\\file_prefix in Windows system], "
                "but received file_prefix is empty string.",
                str(e.exception),
            )

            traced_layer.save_inference_model(path)

    def _train_simple_net(self):
        layer = None
        with base.dygraph.guard():
            layer = SimpleFCLayer(
                self.feature_size, self.batch_size, self.fc_size
            )
            optimizer = paddle.optimizer.SGD(
                learning_rate=1e-3, parameters=layer.parameters()
            )

            for i in range(5):
                in_x = paddle.to_tensor(
                    np.random.random(
                        (self.batch_size, self.feature_size)
                    ).astype('float32')
                )
                dygraph_out = layer(in_x)
                loss = paddle.mean(dygraph_out)
                loss.backward()
                optimizer.minimize(loss)
        return layer


class TestOutVarWithNoneErrMsg(unittest.TestCase):
    def test_linear_net_with_none(self):
        if base.framework.in_dygraph_mode():
            return
        model = LinearNetWithNone(100, 16)
        in_x = paddle.to_tensor(np.random.random((4, 100)).astype('float32'))
        with self.assertRaises(TypeError):
            dygraph_out, traced_layer = base.dygraph.TracedLayer.trace(
                model, [in_x]
            )


class TestTracedLayerSaveInferenceModel(unittest.TestCase):
    """test save_inference_model will automatically create non-exist dir"""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.save_path = os.path.join(self.temp_dir.name, "./nonexist_dir/fc")
        import shutil

        if os.path.exists(os.path.dirname(self.save_path)):
            shutil.rmtree(os.path.dirname(self.save_path))

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_mkdir_when_input_path_non_exist(self):
        if base.framework.in_dygraph_mode():
            return
        fc_layer = SimpleFCLayer(3, 4, 2)
        input_var = paddle.to_tensor(np.random.random([4, 3]).astype('float32'))
        with base.dygraph.guard():
            dygraph_out, traced_layer = base.dygraph.TracedLayer.trace(
                fc_layer, inputs=[input_var]
            )
            self.assertFalse(os.path.exists(os.path.dirname(self.save_path)))
            traced_layer.save_inference_model(self.save_path)
            self.assertTrue(os.path.exists(os.path.dirname(self.save_path)))


if __name__ == '__main__':
    unittest.main()
