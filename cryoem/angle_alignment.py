import tensorflow as tf
from time import time
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns; sns.set(style="white", color_codes=True)
import time
from IPython import display as IPyDisplay
from scipy.spatial.transform import Rotation as R
from cryoem.conversions import euler2quaternion, d_q


def euler6tomarix4d(a_R):
    """ Convert 6D vector containing angles to 4D rotation matrix
    Parameters
    ----------
    a_R : tf.tensor/np.ndarray
        Vector of shape (6,)
    Returns
    -------
    R : tf.tensor/np.ndarray
        4x4 Rotation matrix corresponding to these 6 angles of rotations
    """
    xy, xz, xw, yz, yw, zw = tf.unstack(a_R, axis=-1)
    
    cxy = tf.cos(xy)
    cxz = tf.cos(xz)
    cxw = tf.cos(xw)
    cyz = tf.cos(yz)
    cyw = tf.cos(yw)
    czw = tf.cos(zw)
    
    sxy = tf.sin(xy)
    sxz = tf.sin(xz)
    sxw = tf.sin(xw)
    syz = tf.sin(yz)
    syw = tf.sin(yw)
    szw = tf.sin(zw)
    
    # Note: wasn't able to create it as simple as np.ndarrays...
    Rxy = [[  cxy,  -sxy, [0.0], [0.0]], 
           [  sxy,   cxy, [0.0], [0.0]],
           [[0.0], [0.0], [1.0], [0.0]],
           [[0.0], [0.0], [0.0], [1.0]]]
    Rxy = tf.reshape(tf.convert_to_tensor(Rxy, dtype=tf.float64), (4, 4)) 
    
    Rxz = [[  cxz, [0.0],  -sxz, [0.0]],
           [[0.0], [1.0], [0.0], [0.0]],
           [  sxz, [0.0],   cxz, [0.0]],
           [[0.0], [0.0], [0.0], [1.0]]]
    Rxz = tf.reshape(tf.convert_to_tensor(Rxz, dtype=tf.float64), (4, 4))
    
    Rxw = [[  cxw, [0.0], [0.0],  -sxw],
           [[0.0], [1.0], [0.0], [0.0]],
           [[0.0], [0.0], [1.0], [0.0]], 
           [  sxw, [0.0], [0.0],  cxw]]
    Rxw = tf.reshape(tf.convert_to_tensor(Rxw, dtype=tf.float64), (4, 4))
    
    Ryz = [[[1.0], [0.0], [0.0], [0.0]],
           [[0.0],   cyz,  -syz, [0.0]],
           [[0.0],   syz,   cyz, [0.0]],
           [[0.0], [0.0], [0.0], [1.0]]]
    Ryz = tf.reshape(tf.convert_to_tensor(Ryz, dtype=tf.float64), (4, 4))
    
    Ryw = [[[1.0], [0.0], [0.0], [0.0]],
           [[0.0],   cyw, [0.0],  -syw],
           [[0.0], [0.0], [1.0], [0.0]],
           [[0.0],   syw, [0.0],  cyw]]
    Ryw = tf.reshape(tf.convert_to_tensor(Ryw, dtype=tf.float64), (4, 4))
    
    Rzw = [[[1.0], [0.0], [0.0], [0.0]],
           [[0.0], [1.0], [0.0], [0.0]], 
           [[0.0], [0.0],   czw,  -szw],
           [[0.0], [0.0],   szw,  czw]]
    Rzw = tf.reshape(tf.convert_to_tensor(Rzw, dtype=tf.float64), (4, 4))
  
    R = Rxy @ Rxz @ Rxw @ Ryz @ Ryw @ Rzw

    # check if matrix is orthogonal: R^T @ R - I < 1e-5
    assert tf.reduce_all(tf.less_equal(tf.abs(tf.subtract(tf.transpose(R) @ R, tf.eye(4, 4, dtype=tf.float64))), 1e-5)), "Matrix R (4x4) should be orthogonal!" 
        
    return R


def update_quaternion(m, a_R, q_predicted):
    """Update old quaternion with learned rotation

    Parameters
    ----------
    m : list of 4 floats (-1 or 1)
        List of length 4 containing diagonal values for rotation matrix. It is used for flipping the rotation.
        When diagonal value is -1, it is flipped. Otherwise, it is identity.
    a_R : np.array
        Array of shape (6,) containing the rotation angles used to align the old quaternion to the true one.
    q_predicted : np.ndarray
        Array of shape (N, 4). Quaternions that we will align.
    Returns
    -------
    q_predicted_rotated: np.ndarray
        Array of shape (N, 4). Rotated quaternion
    """
    # 4D matrix rotation
    R = euler6tomarix4d(a_R)
    I = tf.linalg.diag(tf.convert_to_tensor(m, dtype=tf.float64))
    q_predicted_rotated = tf.transpose(R @ I @ tf.transpose(q_predicted))

    return q_predicted_rotated

def loss_alignment(m, a_R, q_predicted, q_true):
    """Loss for optimization
    
    Parameters
    ----------
    m : list of 4 floats (-1 or 1)
        List of length 4 containing diagonal values for rotation matrix. It is used for flipping the rotation.
        When diagonal value is -1, it is flipped. Otherwise, it is identity.
    a_R : np.array
        Array of shape (6,) containing the rotation angles used to align the old quaternion to the true one.
    q_predicted : np.ndarray
        Array of shape (N, 4). Predicted/estimated quaternion.
    q_true : np.ndarray
        Array of shape (N, 4). Ground-truth quaternion.
    
    Returns
    -------
        Loss function specified as a mean of distances between true and predicted quaternion.
    """
    # 4D matrix rotation
    R = euler6tomarix4d(a_R)
    I = tf.linalg.diag(tf.convert_to_tensor(m, dtype=tf.float64))
    q_predicted_rotated = tf.transpose(R @ I @ tf.transpose(q_predicted))

    return tf.reduce_mean(d_q(q_true, q_predicted_rotated))


def gradient_alignment(m, a_R, q_predicted, q_true):
    """Gradion for optimization
     
    Parameters
    ----------
    m : list of 4 floats (-1 or 1)
        List of length 4 containing diagonal values for rotation matrix. It is used for flipping the rotation.
        When diagonal value is -1, it is flipped. Otherwise, it is identity.
    a_R : np.array
        Array of shape (6,) containing the rotation angles used to align the old quaternion to the true one.
    q_predicted : np.ndarray
        Array of shape (N, 4). Predicted/estimated quaternion.
    q_true : np.ndarray
        Array of shape (N, 4). Ground-truth quaternion.

    Returns
    -------
    loss_value : tf.tensor
        Loss value for the optimization
    gradient : tf.tensor
        Gradient value
    """
    with tf.GradientTape() as tape:
        loss_value = loss_alignment(m, a_R, q_predicted, q_true)
        gradient = tape.gradient(loss_value, a_R)
        
    return loss_value, gradient


def training_angle_alignment(num_runs, steps, batch_size, optimizer, angles_true, angles_predicted, threshold=None):
    """Main method for angle alignment

    Parameters
    ----------
    num_runs : int
        Number of times to run angle alignment.
    steps : int
        Number of steps of optimization (gradient update).
    batch_size : int
        The number of training data points utilized in one iteration/step. 
    optimizer : tf.keras.optimizers
        The optimizer used for the ML optimization.
    angles_true : np.ndarray
        Array of shape (N, 3). Ground-truth angles.
    angles_predicted :
        Array of shape (N, 3). Predicted angles.
    threshold : float
        Loss threshold to use for early algorithm stopping.

    Returns
    -------
    m : list of 4 floats (-1 or 1)
        List of length 4 containing diagonal values for rotation matrix. It is used for flipping the rotation.
        When diagonal value is -1, it is flipped. Otherwise, it is identity.
    a_R : np.array
        Array of shape (6,) containing the rotation angles used to align the old quaternion to the true one.
    losses : np.ndarray
        Angle alignment losses.
    collect_data : np.ndarray
        Contains the rotated predicted quaternion from every iteration.
    trajectory : np.ndarray
        Contains the rotation matrices predicted at every step.
    """
    
    def _inner(m, steps, batch_size, optimizer, angles_true, angles_predicted, title):
        """Angle alignment for the single parameter values (not lists of values)"""
        collect_data = []

        time_start = time.time()

        report = ""

        losses = np.empty(steps)
        angles_predicted = tf.convert_to_tensor(angles_predicted)
        learning_rate = optimizer.lr.numpy()

        trajectory = np.zeros([steps + 1, 6])
        euler = tf.random.uniform([6], 0, 2*np.pi, dtype=tf.float64) 
        a_R = [tf.Variable(euler)]
        trajectory[0, :] = a_R[0].numpy()

        q_predicted = euler2quaternion(angles_predicted)
        q_true = euler2quaternion(angles_true)

        for step in range(1, steps+1):

            # Sample some pairs.
            idx = list(np.random.choice(range(len(angles_predicted)), size=batch_size))

            # Compute distances between projections
            qt = [q_true[i]      for i in idx]
            qp = [q_predicted[i] for i in idx]

            # Optimize by gradient descent.
            losses[step-1], gradients = gradient_alignment(m, a_R, qp, qt)
            optimizer.apply_gradients(zip(gradients, a_R))
            trajectory[step, :] = a_R[0].numpy()
            
            update_lr = 300
            if step>update_lr and step%update_lr==0 and losses[step-1]-losses[step-1-update_lr+100] < 0.1:
                learning_rate *= 0.1

            # Visualize progress periodically
            if step % 10 == 0:
                qu = update_quaternion(m, a_R, q_predicted)

                collect_data.append(qu.numpy())

                plt.close();
                sns.set(style="white", color_codes=True)
                sns.set(style="whitegrid")

                fig, axs = plt.subplots(1, 3, figsize=(24,7))
                plt.title(title, fontsize=22)

                # Distance count subplot (batches)
                qpr = update_quaternion(m, a_R, qp)
                d1 = d_q(qpr, qt)
                axs[0].set_xlim(0, np.pi)
                #axs[0].set_ylim(0, batch_size)
                axs[0].set_title(f"BATCHES (size={len(qp)}): [{step}/{steps}] Distances between true and predicted angles \nMEAN={np.mean(d1):.2e} STD={np.std(d1):.2e}")
                s = sns.distplot(d1, kde=False, bins=100, ax=axs[0], axlabel="Distance [rad]", color="r")
                max_count = int(max([h.get_height() for h in s.patches]))
                axs[0].plot([np.mean(d1)]*max_count, np.arange(0, max_count,1), c="r", lw=4)

                # Optimization loss subplot
                axs[1].plot(np.linspace(0, time.time()-time_start, step), losses[:step], marker="o", lw=1, markersize=3)
                axs[1].set_xlabel('time [s]')
                axs[1].set_ylabel('loss');
                axs[1].set_title(f"Angle alignment optimization \nLOSS={np.mean(losses[step-10:step]):.2e} LR={learning_rate:.2e}")

                # Distance count subplot (full)
                q_predicted_rot = update_quaternion(m, a_R, q_predicted)
                d2 = d_q(q_predicted_rot, q_true)
                axs[2].set_xlim(0, np.pi)
                # axs[2].set_ylim(0, len(angles_true))
                axs[2].set_title(f"FULL: [{step}/{steps}] Distances between true and predicted angles\nMEAN={np.mean(d2):.2e} ({np.degrees(np.mean(d2)):.2e} deg) STD={np.std(d2):.2e}\nMEDIAN={np.median(d2):.2e} ({np.degrees(np.median(d2)):.2e} deg)")
                s = sns.distplot(d2, kde=False, bins=100, ax=axs[2], axlabel="Distance [rad]", color="r")
                max_count = int(max([h.get_height() for h in s.patches]))
                axs[2].plot([np.mean(d2)]*max_count, np.arange(0, max_count,1), c="r", lw=4)

                

                IPyDisplay.clear_output(wait=True)
                IPyDisplay.display(plt.gcf())
                plt.close();
                time.sleep(.1)


            # Periodically report progress.
            if ((step % (steps//10)) == 0) or (step == steps):
                time_elapsed = time.time() - time_start
                report += f'step {step}/{steps} ({time_elapsed:.0f}s): loss = {np.mean(losses[step-steps//10:step-1]):.2e}\n'

            if step >= 101 and np.mean(losses[step-101:step-1]) < 1e-3:
                break;

        print(report)
        return m, a_R, losses, np.array(collect_data), trajectory
    
    d = {'m':[], 'a_R':[], 'losses':[], 'collect_data':[], 'trajectory':[]}
    for i in range(num_runs):
        for m in [[1., 1., 1., 1.], [1., 1., 1., -1.]]:
            title = f"run {i+1}/{num_runs+1} | m = {m}"
            m, a_R, losses, collect_data, trajectory = _inner(m, steps, batch_size, optimizer, angles_true, angles_predicted, title)
            d['m'].append(m)
            d['a_R'].append(a_R)
            d['losses'].append(losses)
            d['collect_data'].append(collect_data)
            d['trajectory'].append(trajectory)
            print(losses[-1])
            if threshold and losses[-1] < threshold:
                break;
        if threshold and losses[-1] < threshold:
            break;
    else:
        if threshold:
            plt.clf();
            plt.close();
            IPyDisplay.clear_output(wait=True)
            print(f"Haven't found the solution less than threshold {threshold}")
            return None, None, None, None, None
    
    plt.close();
    IPyDisplay.clear_output(wait=True)
    
    losses = np.array([l[-1] for l in d['losses']])
    idx = np.argmin(losses)
    
    
    # PLOT RESULT
    q_true = euler2quaternion(angles_true)
    q_predicted = euler2quaternion(angles_predicted)
    sns.set(style="white", color_codes=True)
    sns.set(style="whitegrid")

    fig, ax = plt.subplots(figsize=(9,7))
    plt.title(title, fontsize=22)
    # Optimization loss subplot
    #axs[0].plot(d['losses'][idx], marker="o", lw=1, markersize=3)
    #axs[0].set_xlabel('steps [#]')
    #axs[0].set_ylabel('loss');
    #axs[0].set_title(f"Angle alignment optimization \nLOSS={np.mean(d['losses'][idx][-10:-1]):.2e}")

    # Distance count subplot (full)
    q_predicted_rot = update_quaternion(d['m'][idx], d['a_R'][idx], q_predicted)
    d2 = d_q(q_predicted_rot, q_true)
    ax.set_xlim(0, np.pi)
    ax.set_title(f"Distances between true and predicted angles")
    s = sns.distplot(d2, kde=False, bins=100, ax=ax, axlabel="Distance [rad]", color="r")
    #max_count = int(max([h.get_height() for h in s.patches]))
    #ax.plot([np.mean(d2)]*max_count, np.arange(0, max_count,1), c="r", lw=4)
    
    m, a_R, losses, collect_data, trajectory = d['m'][idx], d['a_R'][idx], d['losses'][idx], d['collect_data'][idx], d['trajectory'][idx]
    trajectory_first = trajectory[0]
    loss_first = losses[0]
    trajectory_last = trajectory[-1]
    loss_last = np.median(d2) #losses[-1]

    print("m=", m, "\ntrajectory_first=",trajectory_first, "\nloss_first=",loss_first, "\ntrajectory_last=", trajectory_last, "\nloss_last=", loss_last)
    return m, a_R, losses, collect_data, trajectory
