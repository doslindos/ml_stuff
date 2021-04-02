from .layers import create_weights, create_bias, dense_layer, conv_layer, recurrent_layer
from .. import tf, npprod

def get_numpy_shape(x):
    if hasattr(x, 'numpy'):
        return x.numpy().shape
    else:
        return x.shape

def dense_weights_creation_loop(weights_list, use_bias, weight_dtype, transpose=False):
    # Loop to create dense weights
    # In:
    #   weights_list:               list, From model configurations.py 'Dense' 'weights'
    #   use_bias:                   bool, use biases
    #   weight_dtype:               str, datatype used with weights

    # Create "connections" between every layer
    # Configurations 'weights' represents number of units in a hidden layer,
    # therefore the number of connections between layers is 'weights' list lenght - 1
    
    weights = []
    bias = []
    connections = len(weights_list)-1
    for connection in range(connections):
        if connection < connections:
            #print(connection, connections)
            
            # Define unit amounts
            in_w = weights_list[connection]
            out_w = weights_list[connection+1]

            if transpose:
                bias_num = in_w
            else:
                bias_num = out_w
            
            # Create weights
            w_var = create_weights([in_w, out_w], dtype=weight_dtype)
            
            if use_bias:
                # Create bias
                b_var = create_bias([bias_num], dtype=weight_dtype)
            else:
                b_var = None
        
            weights.append(w_var)
            bias.append(b_var)
        else:
            break

    return (weights, bias)

def dense_transpose_weights_creation_loop(weights_list, bias=None):

    weights = []
    biases = []
    for i, w in enumerate(weights_list):
        w_var = tf.transpose(w)
        if bias[i] is not None:
            b_var = bias[i]
        else:
            b_var = None
        
        weights.append(w_var)
        biases.append(b_var)

    return (weights, bias)

def conv_transpose_weights_creation_loop(weights_list, reversed_bs):
    weights = []
    bias = []
    
    for i, w in enumerate(weights_list):
        w_var = w
        if reversed_bs[i] is not None:
            b_var = reversed_bs[i]
        else:
            b_var = None

        weights.append(w_var)
        bias.append(b_var)

    return (weights, bias)

def conv_weights_creation_loop(kernel_size, filters, use_bias, weight_dtype, transpose):
    # Loop to create convolutional weights
    # In:
    #   filters:                    list, From model configurations.py 'Convo' 'filters'
    #   kernel_size:                list, From model configurations.py 'Convo' 'kernel_size'
    #   use_bias:                   bool, use biases
    #   weight_dtype:               str, datatype used with weights
    #   tranpose:

    # Create "connections" between every layer
    # Configurations 'weights' represents number of units in a hidden layer,
    # therefore the number of connections between layers is 'weights' list lenght - 1
    
    weights = []
    bias = []
    connections = len(filters)-1
    
    for connection in range(connections):
        if connection < connections:
            #print(connection, connections)
            
            # Define conv weight kernel and filter sizes
            k1 = kernel_size[connection][0]
            k2 = kernel_size[connection][1]
            if not transpose:
                f1 = filters[connection]
                f2 = filters[connection+1]
            else:
                f1 = filters[connection+1]
                f2 = filters[connection]
            # Create weights
            w_var = create_weights([k1, k2, f1, f2], dtype=weight_dtype)
            
            if use_bias:
                # Create bias
                b_var = create_bias([f2], dtype=weight_dtype)
            else:
                b_var = None
        
            weights.append(w_var)
            bias.append(b_var)
        else:
            break

    return (weights, bias)

class Layer_Handler:

    def __init__(self):
        self.shapes = {}

    def init_shapes(self, layer_name):
        # Initializes the shapes dict

        if layer_name not in list(self.shapes.keys()):
            self.shapes[layer_name] = {}

    def check_transpose(self, conf):
        # Uses the conf dict to resolve if the layer is transpose layer or not
        
        def add_last_hidden_to_conf():
            # Add last layer to transpose layers
            if isinstance(conf['weights'], list):
                if conf['weights'][-1] != self.out_dense:
                    conf['weights'].append(int(self.out_dense))

        if 'transpose' in list(conf.keys()):
            if 'weights' in list(conf.keys()):
                add_last_hidden_to_conf()
            return conf['transpose']
        elif 'weights' in list(conf.keys()):
            if isinstance(conf['weights'], str):
                add_last_hidden_to_conf()
                return True
            else:
                return False
        else:
            return False

    def handle_dense_input_shape(self, x, conf):
        # Flats the input is not in shape (batch, features)
        # In:
        #   x:                      Tensor, input
        #   conf:                   dict, configuration
        # Out:
        #   x:                      Tensor, shaped or unshaped input
        #   original_shape:         tuple, the shape before flattening
        #   flat_shape:             tuple, shape after flattening

        if len(x.shape) > 2:
            original_shape = get_numpy_shape(x)
            flatted_shape = npprod(x.shape[1:])
            # Flat input if needed
            x = tf.reshape(x, (x.shape[0], flatted_shape))
            # Add flatted layer to weights
            self.original = original_shape
            self.out_dense = flatted_shape
            if conf['weights'][0] != int(flatted_shape):
                conf['weights'].insert(0, int(flatted_shape))
        else:
            original_shape = None
            flatted_shape = None
            if not isinstance(conf['weights'], str):
                if conf['weights'][0] != x.shape[1:][0]:
                    conf['weights'].insert(0, x.shape[1:][0])
        
        return (x, original_shape, flatted_shape)

    def handle_transpose_shape_fetch(self, layer, t_layer_name, w_num):
        
        # Define the correct shapes block
        t_block = self.shapes[t_layer_name]
        
        # Reverse the order of layers
        if not hasattr(self, 'transpose_order'):
            self.transpose_order = list(reversed(sorted(t_block.keys())))
        
        t_layer = self.transpose_order[layer]

        # Last layer takes the out_shape from Input shape
        # Every else takes it from output shape
        if layer != w_num:
            key = 'IN'
        else:
            key = 'OUT'
        
        out_shape = t_block[t_layer][key]
        
        return out_shape

    def initialize_dense_layer(self, layer_name, input_dtype, conf, weights, bias, transpose):
        # Create weights for the DENSE layer if not made
        # In:
        #   conf:                   dict, configuration
        # Out:
        #   (weigths, bias):        (dict, dict) modified weights dicts
        
        if not layer_name in list(weights.keys()):
            if isinstance(conf['weights'], list):
                trainable_vars = True
                # Create new weights
                cws, cbs = dense_weights_creation_loop(
                            conf['weights'], 
                            conf['use_bias'], 
                            input_dtype,
                            transpose
                            )

            elif isinstance(conf['weights'], str):
                trainable_vars = False
                # Configuration should habe the name of the layer whichs weights are used
                layer_to_reverse = conf['weights']
            
                if conf['use_bias']:
                    reversed_bs = list(reversed(bias[layer_to_reverse][1]))
                else:
                    reversed_bs = None

                cws, cbs = dense_transpose_weights_creation_loop(
                    list(reversed(weights[layer_to_reverse][1])),
                    reversed_bs,
                    )
            
            weights[layer_name] = (trainable_vars, cws)
            bias[layer_name] = (trainable_vars, cbs)

        return (weights, bias)
    
    def initialize_conv_layer(self, layer_name, input_dtype, conf, weights, bias, transpose):
        # Create weights for the CONV layer if not made
        # In:
        #   conf:                   dict, configuration
        # Out:
        #   (weigths, bias):        (dict, dict) modified weights dicts
        if not layer_name in list(weights.keys()):
            
            # Use reversed weights
            if isinstance(transpose, str) and 'kernel_sizes' not in conf.keys():
                if conf['use_bias']:
                    reversed_bs = list(reversed(bias[conf['transpose']][1]))
                else:
                    reversed_bs = None
                #print([i.shape for i in weights[conf['transpose']][1]])       
                cws, cbs = conv_transpose_weights_creation_loop(
                    list(reversed(weights[conf['transpose']][1])),
                    reversed_bs,
                    )
                trainable_vars = False
            # Create new weights
            else:
                # Create new weights
                cws, cbs = conv_weights_creation_loop(
                                conf['kernel_sizes'],
                                conf['filters'],
                                conf['use_bias'], 
                                input_dtype,
                                transpose
                                )
                trainable_vars = True


            weights[layer_name] = (trainable_vars, cws)
            bias[layer_name] = (trainable_vars, cbs)

        return (weights, bias)

    def Dense(  self,
                x, 
                weights, 
                bias, 
                conf, 
                layer_name, 
                input_dtype, 
                training=False
                ):

        # Create or load weights to a dense layer
        # In:
        #   x:                          Tensor, input
        #   weights:                    list, of tensorflow weights
        #   conf:                       dict, configurations
        #   layer_name:                 str, name for the layer
        #   input_dtype:                str, datatype for weights
        # Out:
        #   x:                          Tensor, output from the layers
        
        # Initialize the shapes object
        self.init_shapes(layer_name)
        
        # Check if the layer is a transposed layer
        transpose = self.check_transpose(conf)

        # If input is not in shape (batch, features) flat the inputs
        x, original_shape, flatted_shape = self.handle_dense_input_shape(x, conf)
        
        # Initialize layers
        weights, bias = self.initialize_dense_layer(layer_name, input_dtype, conf, weights, bias, transpose)
        
        # Choose weights
        ws = weights[layer_name][1]
        bs = bias[layer_name][1]
        shapes = self.shapes[layer_name]
        # Feed the input through the dense layer
        for layer, w in enumerate(ws):

            if layer not in shapes.keys():
                shapes[layer] = {'IN':get_numpy_shape(x)}
            else:
                shapes[layer]['IN'] = get_numpy_shape(x)
            
            x = dense_layer(
                x, 
                w, 
                bs[layer],
                conf['activations'][layer], 
                conf['dropouts'][layer], 
                training,
                transpose
                )
        
            shapes[layer]['OUT'] = get_numpy_shape(x)
                                
        return x

    def Convo(self,
                x, 
                weights, 
                bias, 
                conf, 
                layer_name, 
                input_dtype, 
                training=False,
                ):

        # Create or load weights to a dense layer
        # In:
        #   x:                          Tensor, input
        #   weights:                    list, of tensorflow weights
        #   conf:                       dict, configurations
        #   layer_name:                 str, name for the layer
        #   input_dtype:                str, datatype for weights
        # Out:
        #   x:                          Tensor, output from the layers

        
        transpose = self.check_transpose(conf)
        
        if len(x.shape) < 4:
            if hasattr(self, 'original'):
                x = tf.reshape(x, self.original)
        
        # Initialize layers
        weights, bias = self.initialize_conv_layer(layer_name, input_dtype, conf, weights, bias, transpose)
        
        # Initialize the shapes object
        self.init_shapes(layer_name)
        
        # Choose weights
        ws = weights[layer_name][1]
        bs = bias[layer_name][1]
        shapes = self.shapes[layer_name]
        
        # Feed the input through the convolutional layer
        for layer, w in enumerate(ws):
            
            if layer not in shapes.keys():
                shapes[layer] = {'IN':get_numpy_shape(x)}
            else:
                shapes[layer]['IN'] = get_numpy_shape(x)
            
            if transpose:
                if 'transpose' in list(conf.keys()):
                    if isinstance(conf['transpose'], str):
                        out_shape = self.handle_transpose_shape_fetch(
                                            layer, 
                                            conf['transpose'], 
                                            len(ws)
                                            )
                    else: # isinstance(transpose, bool):
                        out_shape = self.original

                else:
                    print("In convolutional transpose layers you must have 'transpose' key and its value is the layer name of which is to be transposed...")
                    exit()
            else:
                out_shape = False
            
            x = conv_layer(
                        x, 
                        w,
                        conf['strides'][layer],
                        conf['paddings'][layer],
                        conf['poolings'][layer],
                        bs[layer],
                        conf['activations'][layer], 
                        conf['batch_norms'][layer],
                        conf['dropouts'][layer], 
                        training,
                        out_shape
                        )

            shapes[layer]['OUT'] = get_numpy_shape(x)
        
        return x

    def Recurrent(self,
                x, 
                weights, 
                bias, 
                conf, 
                layer_name, 
                input_dtype, 
                training=False,
                ):

        # Create or load weights to a dense layer
        # In:
        #   x:                          Tensor, input
        #   weights:                    list, of tensorflow weights
        #   conf:                       dict, configurations
        #   layer_name:                 str, name for the layer
        #   input_dtype:                str, datatype for weights
        # Out:
        #   x:                          Tensor, output from the layers

        # Initialize the shapes object
        self.init_shapes(layer_name)
        
        # Check if the layer is a transposed layer
        transpose = self.check_transpose(conf)

        # If input is not in shape (batch, features) flat the inputs
        x, original_shape, flatted_shape = self.handle_dense_input_shape(x, conf)
        
        # Initialize layers
        weights, bias = self.initialize_dense_layer(conf, weights, bias)
    
        # Choose weights
        ws = weights[layer_name][1]
        bs = bias[layer_name][1]
        shapes = self.shapes[layer_name]
        # Feed the input through the dense layer
        for layer, w in enumerate(ws):

            if layer not in shapes.keys():
                shapes[layer] = {'IN':get_numpy_shape(x)}
            else:
                shapes[layer]['IN'] = get_numpy_shape(x)
            
            x = recurrent_layer(
                x, 
                w, 
                bs[layer],
                conf['activations'][layer], 
                conf['dropouts'][layer], 
                training,
                transpose
                )
        
            shapes[layer]['OUT'] = get_numpy_shape(x)
                                
        return x