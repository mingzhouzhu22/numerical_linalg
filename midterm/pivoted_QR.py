import numpy as np
import numpy.linalg as la
from scipy.linalg import solve_triangular
from time import clock
import matplotlib.pyplot as plt
import csv

def ej(d,j=0):
    """
    Return the e_k-th basis vector of dimension d, starting at 0.
    """
    res = np.zeros(d)
    res[j] = 1
    return res

def sign(a):
    """
    Return the sign of a real number, or the complex phase for a complex number
    """
    if a == 0:
        return 1
    else: return a/abs(a)

def swap_rows(mat, i, j):
    tmp = mat[i].copy()
    mat[i] = mat[j]
    mat[j] = tmp

def formQ(W, swaps = None):
    """
    Make a reduced Q matrix from the v-s in W
    If swaps is not empty, it contains a list of integer indexes corresponding to permuatations.
    In particular, swaps[k] is the row number that was swapped with the k-th row at the k-th step.
    """
    m,n = W.shape
    Q = np.zeros((m,n), dtype = W.dtype)

    for k in range(n)[::-1]:
        Q[:,k] = ej(m, k)
        v = W[k:,k]
        dim = len(v)
        Q[k:,k:] -= 2*np.dot(v.reshape((dim,1)), np.dot(v.reshape((1,dim)).conj(), Q[k:,k:]))
        if swaps is not None:
            #We multiply on the left by the inverse of the swap matrix, which is just the same as the original swap because swapping twice is the identity transformation
            swap_rows(Q, k, swaps[k])
    return Q

def invert_permutation(p):
    l = len(p)
    res = p.copy()
    for k in xrange(len(p)):
        res[p[k]] = k
    return res

def formp(col_swaps):
    """
    Given the column swaps performed while pivoting, contruct the appropriate permutation of the columns of A
    """
    n = len(col_swaps)
    p = np.arange(n)
    for k in range(n):
        t = p[k]
        p[k] = p[col_swaps[k]]
        p[col_swaps[k]] = t
    return p

def house(A):
    """
    Compute the implicit QR decomposition of a mxn complex numpy matrix A.
    Returns:
        W -- A lower-triangular complex mxn matrix, whose columns are the vs used for householder reflections.
        R -- The upper triangular nxn matrix in the QR decomposition.
    """
    m, n = A.shape
    if n > m: raise ValueError("The array must NOT have more columns than rows")

    R = A.copy()
    W = np.zeros(A.shape, dtype = R.dtype)

    for k in xrange(n):
        #select out the x-vector in the k-th column of R that needs to be reflected onto the span of e_1
        x = R[k:, k]
        dim = m-k
        #now pick an appropriate v for the Householder reflection
        v =  sign(x[0]) * la.norm(x) * ej(dim) + x
        v = v/la.norm(v)
        W[k:, k] = v
        #Multiply the appropriate submatrix of A by the reflector
        R[k:,k:] -= 2*np.dot(v.reshape((dim, 1)), np.dot(v.reshape((1,dim)).conj(), R[k:,k:]))

    return W, R[:n, :n]

def pivoted_QR(A):
    """
    Description:
        A function to compute a pivoted QR factorization AP=QR, with the diagonal entries of R monotonically decreasing in magnitude.
        We compute this by a column pivoting approach, where at each step we operate on the column with biggest norm among the candidates
        This works because the diagonal entries of R are precisely the norms of the x vectors used to pick the reflector at each step
        Also reflectors preserve norms and truncation decreases them, which is all we need to prove the result
    Arguments:
        A -- A complex valued mxn matrix, m >= n.
    Returns: (p,Q,R)
        p -- a vector containing the n permuted indices corresponding to the permutation matrix P with AP = QR
        Q -- an mxn matrix with orthonormal columns
        R -- an nxn upper triangular matrix with abs(R[0,0]) >= abs(R[1,1]) >= ... >= abs(R[-1, -1])
    """
    m, n = A.shape
    dtype = A.dtype
    if not dtype == np.complex128: dtype = np.float64
    R = A.astype(dtype).copy()
    W = np.zeros(A.shape, dtype = R.dtype)
    col_swaps = np.zeros(n, dtype=int)
    for k in xrange(n):
        view = R[k:,k:]
        #find and store the column with biggest norm (in the submatrix)
        c = np.argmax(la.norm(R[k:,k:], axis=0))
        col_swaps[k] = c+k

        #swap columns
        tmp_col = R[:,col_swaps[k]].copy()
        R[:,col_swaps[k]] = R[:,k]
        R[:,k] = tmp_col

        #Compute the Householder reflection
        x = view[:,0]
        dim = m-k
        v =  sign(x[0]) * la.norm(x) * ej(dim) + x
        v = v/la.norm(v)
        W[k:, k] = v

        #Multiply the submatrix by the reflector
        R[k:,k:] -= 2*np.dot(v.reshape((dim, 1)), np.dot(v.reshape((1,dim)).conj(), R[k:,k:]))

    Q = formQ(W)
    R = R[:n,:n]
    p = formp(col_swaps)
    return p, Q, R[:n,:n]


def complete_pivoted_QR(A):
    """
    This function computes a version of QR factorization that does complete pivoting
    At each step k, the entry with biggest magnitude in the R[k:, k:] submatrix is pivoted into the k,k spot
    Not sure what stability properties this has, but it solves Problem 3 a good amount of the time
    I did a lot of work to get the row pivoting working Can I have extra credit?
    We can absorb the row pivoting matrices into the Q's, so it still computes a column pivoted AP = QR factorization
    """

    m, n = A.shape
    dtype = A.dtype
    if not dtype == np.complex128: dtype = np.float64
    R = A.astype(dtype).copy()
    W = np.zeros(A.shape, dtype = R.dtype)
    row_swaps = np.zeros(n, dtype=int)
    col_swaps = np.zeros(n, dtype=int)
    for k in xrange(n):
        view = R[k:,k:]
        #find and store the location of the submatrix entry with largest magnitude
        r, c = np.unravel_index(np.argmax(np.abs(R[k:,k:])), (m-k,n-k))
        row_swaps[k] = r+k
        col_swaps[k] = c+k

        #swap rows
        swap_rows(R, k, row_swaps[k])

        #swap columns
        tmp_col = R[:,col_swaps[k]].copy()
        R[:,col_swaps[k]] = R[:,k]
        R[:,k] = tmp_col

        #Compute the Householder reflection
        x = view[:,0]
        dim = m-k
        v =  sign(x[0]) * la.norm(x) * ej(dim) + x
        v = v/la.norm(v)
        W[k:, k] = v

        #Multiply the submatrix by the reflector
        R[k:,k:] -= 2*np.dot(v.reshape((dim, 1)), np.dot(v.reshape((1,dim)).conj(), R[k:,k:]))

    Q = formQ(W, swaps=row_swaps)
    R = R[:n,:n]
    p = formp(col_swaps)
    return p, Q, R[:n,:n]


def pivoted_least_squares(A, b):
    p, Q, R = pivoted_QR(A)
    v = solve_triangular(R, Q.T.conj().dot(b))
    #permute v
    #NOTE: Mutliplying on the left by P permutes rows inversely to the way P permutes columns
    return v[invert_permutation(p)]

def compare_lstsq(m,n):
    """
    Description:
        Compares the peformance of a built-in least squares solver to my own on a random system Ax=b
         where A is of size m x n and b of size m
    Returns:
        t1 -- the time for the built-in least squares
        t2 -- the time for my pivoted least squares
    """
    A = np.random.random((m,n))
    b = np.random.random(m)
    s = clock()
    x1 = la.lstsq(A,b)[0]
    t1 = clock()-s
    s = clock()
    x2 = pivoted_least_squares(A,b)
    t2 = clock()-s
    assert np.allclose(x1, x2)
    return t1, t2

def do_least_squares_comp():
    ratios = [2,4,8]
    for ind, r in enumerate(ratios):
        bl, ml = [],[]
        #for smaller m we can have a bigger value of m
        ms = [2**i for i in xrange(4,12+ind)]
        ns = []
        for m in ms:
            n = m/r
            ns.append(n)
            built_time, my_time = compare_lstsq(m, n)
            bl.append(built_time)
            ml.append(my_time)
            print "m={}, n={}".format(m,n)
            print "Built in: {}, Mine: {}".format(built_time, my_time)

        fig, axs = plt.subplots(1,1)
        p = axs
        p.plot(ms, bl, label="Built-in solver", marker="^", linestyle="--", markersize=20)
        p.plot(ms, ml, label="My pivoted QR", marker="^", linestyle="--", markersize=20)
        p.legend(loc="upper left")
        p.set_ylabel("runtime (seconds)")
        p.set_xlabel("m")
        p.set_xscale('log')
        p.set_yscale('log')
        p.set_title("Comparison of times when m = {}*n".format(r))
        plt.savefig("prob4_c_{}.png".format(r))
        plt.show()

        w = csv.writer(open('prob4_c_{}.csv'.format(r), "w"))
        #write header row
        w.writerow(["My pivoted QR", "Numpy's built-in", "m", "n"])
        #then write each
        for t in zip(ml, bl, ms, ns):
            w.writerow(t)


if __name__ == "__main__":
    do_least_squares_comp()
