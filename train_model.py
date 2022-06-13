import os
import random
import time
from keras.preprocessing.image import ImageDataGenerator
from keras.models import Sequential
from keras.layers import Conv2D, MaxPooling2D
from keras.layers import Activation, Dropout, Flatten, Dense
from keras import backend as K
import tempfile
import shutil

from data_statistics import get_class_stats, print_statistics


def copy_list_of_files(file_list, desitation_dir):
    for file_name in file_list:
        shutil.copy2(file_name, desitation_dir)


def copy_files_to_temp(classes, train_data_dir):
    temp_train_dir = tempfile.mkdtemp()
    temp_validate_dir = tempfile.mkdtemp()

    class_stats = get_class_stats(classes, train_data_dir)
    print("Input data stats:")
    print_statistics(class_stats)

    # get value to normalize training data count
    smallest_class_size = min(class_stats.values())

    for class_name in classes:
        class_data_dir = os.path.join(train_data_dir, class_name)

        # make dir for class in temp dirs
        os.makedirs(os.path.join(temp_train_dir, class_name))
        os.makedirs(os.path.join(temp_validate_dir, class_name))

        # get file list for class cut to smallest class size
        file_names = [os.path.join(class_data_dir, file_name) for file_name in next(
            os.walk(class_data_dir), (None, None, []))[2]][:smallest_class_size]

        # calculate sample sizes
        validation_proportion = 0.2
        validate_sample_size = int(
            len(file_names) * validation_proportion)

        # create train and validate samples
        validate_sample = random.sample(
            file_names, validate_sample_size)
        train_sample = [
            x for x in file_names if x not in validate_sample]

        # copy samples into directories
        copy_list_of_files(validate_sample, os.path.join(
            temp_validate_dir, class_name))
        copy_list_of_files(train_sample, os.path.join(
            temp_train_dir, class_name))

    print("Normalized training data stats:")
    print("Input data stats:")
    print_statistics(get_class_stats(classes, temp_train_dir))
    print("Normalized validation data stats:")
    print_statistics(get_class_stats(classes, temp_validate_dir))

    return temp_train_dir, temp_validate_dir


def prep_files_for_training(classes):
    module_path = os.path.dirname(os.path.realpath(__file__))
    train_data_dir = os.path.join(module_path, 'data', 'train')

    model_path = os.path.join(
        module_path,
        "models",
        str(int(time.time())),
        "model_saved.m5"
    )

    temp_train_dir, temp_validate_dir = copy_files_to_temp(
        classes, train_data_dir)

    return temp_train_dir, temp_validate_dir, model_path


def compile_model(img_width, img_height):
    # reference https://www.geeksforgeeks.org/python-image-classification-using-keras/
    if K.image_data_format() == 'channels_first':
        input_shape = (3, img_width, img_height)
    else:
        input_shape = (img_width, img_height, 3)

    model = Sequential()
    model.add(Conv2D(32, (2, 2), input_shape=input_shape))
    model.add(Activation('relu'))
    model.add(MaxPooling2D(pool_size=(2, 2)))

    model.add(Conv2D(32, (2, 2)))
    model.add(Activation('relu'))
    model.add(MaxPooling2D(pool_size=(2, 2)))

    model.add(Conv2D(64, (2, 2)))
    model.add(Activation('relu'))
    model.add(MaxPooling2D(pool_size=(2, 2)))

    model.add(Flatten())
    model.add(Dense(128))
    model.add(Activation('relu'))
    model.add(Dropout(0.5))
    model.add(Dense(1))
    model.add(Activation('softmax'))

    model.compile(loss='binary_crossentropy',
                  optimizer='rmsprop',
                  metrics=['accuracy'])

    return model


def train_model(train_data_dir, validation_data_dir, img_width, img_height, nb_train_samples, nb_validation_samples, epochs, batch_size, model, model_path):
    # reference https://www.geeksforgeeks.org/python-image-classification-using-keras/
    train_datagen = ImageDataGenerator(
        rescale=1. / 255,
        shear_range=0.2,
        zoom_range=0.2,
        horizontal_flip=True)

    test_datagen = ImageDataGenerator(rescale=1. / 255)

    train_generator = train_datagen.flow_from_directory(
        train_data_dir,
        target_size=(img_width, img_height),
        batch_size=batch_size,
        class_mode='binary')

    validation_generator = test_datagen.flow_from_directory(
        validation_data_dir,
        target_size=(img_width, img_height),
        batch_size=batch_size,
        class_mode='binary')

    model.fit_generator(
        train_generator,
        steps_per_epoch=nb_train_samples // batch_size,
        epochs=epochs,
        validation_data=validation_generator,
        validation_steps=nb_validation_samples // batch_size)

    model.save_weights(model_path)


img_width, img_height = 290, 325
classes = ["A1", "A3", "B1", "B3", "C1", "C3", "None"]


train_data_dir, validation_data_dir, model_path = prep_files_for_training(
    classes)

train_size = get_class_stats(classes, train_data_dir)[classes[0]]
validation_size = get_class_stats(classes, validation_data_dir)[classes[0]]

epochs = 50
batch_size = 15

model = compile_model(img_width, img_height)

train_model(train_data_dir, validation_data_dir, img_width, img_height,
            train_size, validation_size, epochs, batch_size, model, model_path)

shutil.rmtree(train_data_dir)
shutil.rmtree(validation_data_dir)
