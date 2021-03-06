import tensorflow as tf
import time
import layer
import math

mnist = None


def get_mnist_data():
    global mnist
    if mnist == None:
        from tensorflow.examples.tutorials.mnist import input_data
        mnist = input_data.read_data_sets('./cache', one_hot=True)
    return mnist


def model_wrapper(handler, size=28):
    # inputs
    tf.reset_default_graph()

    x = tf.placeholder(tf.float32, [None, size * size])
    y_ = tf.placeholder(tf.float32, [None, 10])
    keep_prob = tf.placeholder(tf.float32)
    learning_rate = tf.placeholder(tf.float32)
    training = tf.placeholder(tf.bool)
    h_pool = tf.reshape(x, [-1, size, size, 1])

    h_pool = handler.convolve(h_pool, training,  keep_prob)
    y = tf.reshape(h_pool, [-1, 10])

    loss = tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits(logits=y, labels=y_))

    # addition of tf.GraphKeys.UPDATE_OPS dependency for batch normalization handling
    update_ops = tf.get_collection(tf.GraphKeys.UPDATE_OPS)
    with tf.control_dependencies(update_ops):
        train = tf.train.RMSPropOptimizer(learning_rate).minimize(loss)

    # Test trained model
    correct_prediction = tf.equal(tf.argmax(y, 1), tf.argmax(y_, 1))
    percent_correct = tf.reduce_mean(tf.cast(correct_prediction, tf.float32))

    return x, y_, keep_prob, loss, train, percent_correct, training, learning_rate


def scale(index, max_index):
    return 0.5 * (1.0 + math.cos(math.pi * index / max_index))


def train_model_and_report(model, data=None, learning_rate_value=1e-4, epochs=200, keep_prob_value=0.5):
    print "MODEL :", model.__class__.__name__
    x, y_, keep_prob, loss, train, percent_correct, training, learning_rate = model_wrapper(model)
    if data == None:
        data = get_mnist_data()

    with tf.Session() as sess:
        sess.run(tf.global_variables_initializer())

        items_per_batch = 200
        start_time = time.time()

        lambda_error = 100.0
        lambda_val = 0.3

        for epoch in range(epochs):
            batches = int(data.test.labels.shape[0] / items_per_batch)
            training_loss = 0.0
            for batch in range(batches):
                batch_xs, batch_ys = data.train.next_batch(items_per_batch)
                result_loss, _ = sess.run([loss, train], feed_dict={
                    x: batch_xs, y_: batch_ys,
                    keep_prob: keep_prob_value, training: True, learning_rate: learning_rate_value * scale(epoch * batches + batch, epochs * batches)})
                training_loss += result_loss

            training_loss *= 1.0 * items_per_batch / data.test.labels.shape[0]

            if (epoch + 1) % 5 == 0:
                print "\tEpoch %5d" % epoch, ", Scaling %0.2f" % scale(epoch * batches, epochs * batches), ", Training Loss %0.4f" % training_loss,
                correct = 0.0
                test_loss = 0.0
                for test_batch in range(100):
                    test_batch_start = test_batch * 100
                    test_batch_end = test_batch_start + 100
                    result_loss, result_correct = sess.run([loss, percent_correct], feed_dict={
                        x: data.test.images[test_batch_start:test_batch_end],
                        y_: data.test.labels[test_batch_start:test_batch_end],
                        keep_prob: 1.0, training: False})
                    test_loss += result_loss
                    correct += result_correct
                # correct /= 100.0
                test_loss /= 100.0
                if lambda_error == 100.0:
                    lambda_error = (100.0 - correct)
                else:
                    lambda_error = lambda_error * (1.0 - lambda_val) + (100.0 - correct) * lambda_val
                print ", Test Loss %0.4f" % test_loss,
                print ", Train/Test %4.2f" % (training_loss / test_loss), ", Percent Error = %4.2f" % (100.0 - correct),
                print ", Lambda Error %4.2f" % lambda_error,
                print ", ", int(time.time() - start_time), "sec"
                if training_loss / test_loss < 0.01:
                    print "End condition met.  Rule 'training_loss / test_loss < 0.01'.  Possible overfitting."
                    return lambda_error

    return lambda_error


class simpleModel:

    def convolve(self, image, training,  keep_prob):
        result = layer.conv_relu(image, 1, 24, width=28, padding="VALID")
        result = tf.nn.dropout(result, keep_prob)
        return layer.conv(result, 24, 10, width=1, padding="VALID")


if __name__ == '__main__':
    train_model_and_report(simpleModel(), epochs=20, learning_rate_value=1e-2)
