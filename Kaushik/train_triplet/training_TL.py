from __future__ import division
from __future__ import print_function
import copy
import time
import torch
import torch.nn.functional as F
from tqdm import tqdm


def train_model_TL(model, dataloaders, criterion, optimizer, device, num_epochs=25, is_inception=False):
    since = time.time()

    train_acc_history = []
    val_acc_history = []

    best_model_wts = copy.deepcopy(model.state_dict())
    best_acc = 0.0

    for epoch in range(num_epochs):
        print('Epoch {}/{}'.format(epoch, num_epochs - 1))
        print('-' * 10)

        # Each epoch has a training and validation phase
        for phase in ['train', 'val']:
            if phase == 'train':
                model.train()  # Set model to training mode
            else:
                model.eval()   # Set model to evaluate mode

            running_loss = 0.0
            running_corrects = 0

            progress = list(range(len(dataloaders[phase])))
            # Iterate over data.
            with tqdm(total=len(progress)) as pbar:
                for inputs, _ in dataloaders[phase]:
                    # We don't need the labels, we know what they are
                   
                    inputs = [inputs[:,k,:,:,:] for k in range(3)]
                    for x in inputs:
                        x = x.to(device)
                        
                    # zero the parameter gradients
                    optimizer.zero_grad()

                    pbar.update(1)
                    # forward
                    # track history if only in train
                    with torch.set_grad_enabled(phase == 'train'):
                        # Get model outputs and calculate loss
                        # Special case for inception because in training it has an auxiliary output. In train
                        #   mode we calculate the loss by summing the final output and the auxiliary output
                        #   but in testing we only consider the final output.
                        if is_inception and phase == 'train':
#                             # From https://discuss.pytorch.org/t/how-to-optimize-inception-model-with-auxiliary-classifiers/7958
#                             outputs, aux_outputs = model(inputs)
#                             loss1 = criterion(outputs, labels)
#                             loss2 = criterion(aux_outputs, labels)
#                             loss = loss1 + 0.4*loss2
                            pass
                        else:
                            outputs = [model(x) for x in inputs]
                            loss = criterion(outputs)

                        if criterion.norm:
                            # Normalize outputs
                            for x in outputs:
                                x = F.normalize(x, p=2, dim=1)
                        # Compute squared l2 distance and loss
                        dist_pos = torch.sum(torch.pow(outputs[0] - outputs[1], 2), dim=1)
                        dist_neg = torch.sum(torch.pow(outputs[0] - outputs[2], 2), dim=1)
                        
                        correct = dist_neg > dist_pos

                        # backward + optimize only if in training phase
                        if phase == 'train':
                            loss.backward()
                            optimizer.step()

                    # statistics
                    running_loss += loss.item() * inputs[0].size(0)
                    running_corrects += torch.sum(correct)

            epoch_loss = running_loss / len(dataloaders[phase].dataset)
            epoch_acc = running_corrects.double() / len(dataloaders[phase].dataset)

            print('{} Loss: {:.4f} Acc: {:.4f}'.format(phase, epoch_loss, epoch_acc))

            # deep copy the model
            if phase == 'val' and epoch_acc > best_acc:
                best_acc = epoch_acc
                best_model_wts = copy.deepcopy(model.state_dict())
            if phase == 'val':
                val_acc_history.append(epoch_acc)
            if phase == 'train':
                train_acc_history.append(epoch_acc)

        print()

    time_elapsed = time.time() - since
    print('Training complete in {:.0f}m {:.0f}s'.format(time_elapsed // 60, time_elapsed % 60))
    print('Best val Acc: {:4f}'.format(best_acc))

    # load best model weights
    model.load_state_dict(best_model_wts)
    return model, val_acc_history, train_acc_history
