# Models for Spotify features of billboard list songs

conf = {
    'train_params':{
        'batch_size':100, 
        'epochs':10, 
        'learning_rate':0.001, 
        'loss_function':'cross_entropy',
        'optimization_function':'classifier'
        },
    'input_shape':[12],
    'data_type':'float32',
    'output_shape':[7],
    'layers':{
        'Dense': {
            'weights':[10, 7],
            'use_bias':True,
            'activations':['relu', None],
            'dropouts':[None, None]
        },
    },

}
