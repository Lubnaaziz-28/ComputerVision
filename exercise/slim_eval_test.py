from datasets import dataset_factory
import tensorflow as tf
import matplotlib.pyplot as plt
import tensorflow.contrib.slim as slim
from nets import nets_factory
from preprocessing import preprocessing_factory
import numpy as np
import math


class SlimEvalMgr(object):
    def __init__(self):
        self.dataset_name = 'flowers'
        self.dataset_split_name = 'validation'
        self.dataset_dir = '/home/levin/workspace/detection/data/flower'
        
        self.batch_size = 100
        self.labels_offset = 0
        self.eval_image_size = None
        self.preprocessing_name = None
        self.model_name = 'inception_v3'
        
        self.num_preprocessing_threads = 4
        
        self.checkpoint_path =  '/tmp/tfmodel/'
        self.eval_dir = '/tmp/tfmodel/'
        
        
        return
    
    def __get_images_labels(self):
        dataset = dataset_factory.get_dataset(
                self.dataset_name, self.dataset_split_name, self.dataset_dir)
        
        provider = slim.dataset_data_provider.DatasetDataProvider(
                dataset,
                shuffle=False,
                common_queue_capacity=2 * self.batch_size,
                common_queue_min=self.batch_size)
        [image_raw, label] = provider.get(['image', 'label'])
        label -= self.labels_offset
        
        network_fn = nets_factory.get_network_fn(
                self.model_name,
                num_classes=(dataset.num_classes - self.labels_offset),
                is_training=False)
        
        preprocessing_name = self.preprocessing_name or self.model_name
        image_preprocessing_fn = preprocessing_factory.get_preprocessing(
                preprocessing_name,
                is_training=False)

        eval_image_size = self.eval_image_size or network_fn.default_image_size

        image = image_preprocessing_fn(image_raw, eval_image_size, eval_image_size)
        
        # Preprocess the image for display purposes.
        image_raw = tf.expand_dims(image_raw, 0)
        image_raw = tf.image.resize_images(image_raw, [eval_image_size, eval_image_size])
        image_raw = tf.squeeze(image_raw)

        images, labels, image_raws = tf.train.batch(
                [image, label, image_raw],
                batch_size=self.batch_size,
                num_threads=self.num_preprocessing_threads,
                capacity=5 * self.batch_size)
        
        self.network_fn = network_fn
        self.dataset = dataset
        
        return images, labels,image_raws
    def __setup_eval(self, images, labels,image_raws):
        tf_global_step = slim.get_or_create_global_step()
        
        logits, _ = self.network_fn(images)
        variables_to_restore = slim.get_variables_to_restore()
        predictions = tf.argmax(logits, 1)
        labels = tf.squeeze(labels)
        
        # Define the metrics:
        names_to_values, names_to_updates = slim.metrics.aggregate_metric_map({
                'Accuracy': slim.metrics.streaming_accuracy(predictions, labels),
                'Recall_5': slim.metrics.streaming_recall_at_k(
                        logits, labels, 5),
        })
        
        # Print the summaries to screen.
        for name, value in names_to_values.items():
            summary_name = 'eval/%s' % name
            op = tf.summary.scalar(summary_name, value, collections=[])
            op = tf.Print(op, [value], summary_name)
            tf.add_to_collection(tf.GraphKeys.SUMMARIES, op)
        
        num_batches = math.ceil(self.dataset.num_samples / float(self.batch_size))
        
        if tf.gfile.IsDirectory(self.checkpoint_path):
            checkpoint_path = tf.train.latest_checkpoint(self.checkpoint_path)
        else:
            checkpoint_path = self.checkpoint_path

#         tf.logging.info('Evaluating %s' % checkpoint_path)

#         slim.evaluation.evaluate_once('',
#                 checkpoint_path=checkpoint_path,
#                 logdir=self.eval_dir,
#                 num_evals=num_batches,
#                 eval_op=list(names_to_updates.values()),
#                 variables_to_restore=variables_to_restore)
        
        #Display images
        probabilities = tf.nn.softmax(logits)
        init_fn = slim.assign_from_checkpoint_fn(
              checkpoint_path,
              slim.get_variables_to_restore())
        with tf.Session() as sess:
            with slim.queues.QueueRunners(sess):
                sess.run(tf.local_variables_initializer())
                init_fn(sess)
                np_probabilities, np_image_raws, np_labels = sess.run([probabilities, image_raws, labels])
        
                for i in range(self.batch_size): 
                    image = np_image_raws[i, :, :, :]
                    true_label = np_labels[i]
                    predicted_label = np.argmax(np_probabilities[i, :])
                    predicted_name = self.dataset.labels_to_names[predicted_label]
                    true_name = self.dataset.labels_to_names[true_label]
                    
                    plt.figure()
                    plt.imshow(image.astype(np.uint8))
                    plt.title('Ground Truth: [%s], Prediction [%s]' % (true_name, predicted_name))
                    plt.axis('off')
                    plt.show()
        
        
        return
    
    
    def run(self):
        tf.logging.set_verbosity(tf.logging.INFO)
        
        self.checkpoint_path = '/tmp/flowers-models/inception_v3'
        self.eval_dir = '/tmp/flowers-models/inception_v3/eval'
        self.dataset_name = 'flowers'
        self.dataset_split_name= 'validation'
        self.dataset_dir= '/home/levin/workspace/detection/data/flower'
        self.model_name = 'inception_v3'
        
        
        self.checkpoint_path = '/tmp/flowers-models/inception_v3/all'
        self.eval_dir = '/tmp/flowers-models/inception_v3/eval/all'
        images, labels,image_raws = self.__get_images_labels()
        self.__setup_eval(images, labels,image_raws)
        
        
        return
    
    


if __name__ == "__main__":   
    obj= SlimEvalMgr()
    obj.run()