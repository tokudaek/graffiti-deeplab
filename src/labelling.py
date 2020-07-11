#!/usr/bin/env python3
"""Analyze labels generated by mannual classification of the crops
"""

import argparse
import time
from os.path import join as pjoin
import os
import inspect

import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FormatStrFormatter
import matplotlib.collections as mc
import matplotlib.patches as mpatches
import pandas as pd
from scipy.spatial import cKDTree
import scipy.stats as stats
import igraph
import geopandas as geopd
import matplotlib_venn
from src.utils import info, export_individual_axis, hex2rgb

palettehex = ['#8dd3c7','#bebada','#fb8072','#80b1d3','#fdb462','#b3de69']
palette = hex2rgb(palettehex, normalized=True, alpha=1.0)

##########################################################
def plot_types(infomapout, shppath, clulabelspath, outdir):
    np.random.seed(0)
    df = pd.read_csv(clulabelspath, index_col='id')
    totalrows = len(df)

    fig, ax = plt.subplots(1, 1, figsize=(15/2, 10), squeeze=False) # Plot contour
    geodf = geopd.read_file(shppath)
    shapefile = geodf.geometry.values[0]
    
    xs, ys = shapefile.exterior.xy
    ax[0, 0].plot(xs, ys, c='dimgray')

    clusters = np.unique(df.cluster)
    clusters_str = ['C{}'.format(cl) for cl in clusters]
    nclusters = len(clusters)
    labels = np.unique(df.label)
    nlabels = len(labels)

    markers = ['$A$', '$B$', '$C$']
    ss = [30, 35, 35]
    edgecolours = ['#993333', '#339933', '#3366ff']
    # edgecolours = ['#0000FF', '#FF0000', '#00FF00']
    visual = [ dict(marker=m, s=s, edgecolors=e) for m,s,e in \
              # zip(['x', '^', 'o'], ss, edgecolours)]
              zip(['o', 'o', 'o'], ss, edgecolours)]
              # zip(markers, ss, edgecolours)]

    for i, l in enumerate(labels):
        data = df[df.label == l]
        ax[0, 0].scatter(data.x, data.y, c=edgecolours[i],
                         label='Type ' + markers[i],
                         alpha=0.6,
                         # linewidths=0.2,
                         # edgecolor=(0.3, 0.3, 0.3, 1),
                         **(visual[i]))
    
    fig.patch.set_visible(False)
    ax[0, 0].axis('off')
    # -46.826198999999995 -46.36508400000003 -24.008430999701822 -23.356292999687376

    ax[0, 0].legend(loc=(0.6, 0.12), title='Graffiti types',
                    fontsize='xx-large', title_fontsize='xx-large')

    extent = ax[0, 0].get_window_extent().transformed(fig.dpi_scale_trans.inverted())
    fig.savefig(pjoin(outdir, 'map_types.pdf'), bbox_inches=extent.expanded(1.0, 1.0))
    fig.savefig(pjoin(outdir, 'map_types.png'), bbox_inches=extent.expanded(1.0, 1.0))

##########################################################
def plot_communities(infomapout, graphmlpath, shppath, outdir):
    """Plot infomap output """
    info(inspect.stack()[0][3] + '()')
    colours = palette
    fig, ax = plt.subplots(1, 1, figsize=(15/2, 9), squeeze=False) # Plot contour

    g = igraph.Graph.Read(graphmlpath)
    g.simplify()
    g.to_undirected()
    coords = [(float(x), -float(y)) for x, y in zip(g.vs['x'], g.vs['y'])]

    fh = open(infomapout)
    lines = fh.read().strip().split('\n')

    aux = np.zeros(g.vcount())
    for l in lines[2:]:
        arr = l.split(' ')
        aux[int(arr[0])-1] = int(arr[1])
    g.vs['clustid'] = aux
    fh.close()

    info('Clusters found in infomap: {}'.format(np.unique(g.vs['clustid'])))

    for attr in ['ref', 'highway', 'osmid', 'id']:
        del(g.vs[attr])
    for attr in g.es.attributes():
        del(g.es[attr])

    coords = [(float(x), -float(y)) for x, y in zip(g.vs['x'], g.vs['y'])]
    coordsnp = np.array([[float(x), float(y)] for x, y in zip(g.vs['x'], g.vs['y'])])
    # vcolours = [palette[int(v['clustid']-1)] for v in g.vs() ]

    clustids = np.array(g.vs['clustid']).astype(int)
    ecolours = np.zeros((g.ecount(), 4), dtype=float)
    lines = np.zeros((g.ecount(), 2, 2), dtype=float)

    for i, e in enumerate(g.es()):
        srcid = int(e.source)
        tgtid = int(e.target)

        ecolours[i, :] = palette[int(g.vs[srcid]['clustid'])-1]

        if g.vs[tgtid]['clustid'] != g.vs[tgtid]['clustid']:
            ecolours[i, 3] = 0.0

        lines[i, 0, 0] = g.vs[srcid]['x']
        lines[i, 0, 1] = g.vs[srcid]['y']
        lines[i, 1, 0] = g.vs[tgtid]['x']
        lines[i, 1, 1] = g.vs[tgtid]['y']

    lc = mc.LineCollection(lines, colors=ecolours, linewidths=0.5)
    ax[0, 0].add_collection(lc)
    ax[0, 0].autoscale()

    geodf = geopd.read_file(shppath)
    shapefile = geodf.geometry.values[0]
    xs, ys = shapefile.exterior.xy
    ax[0, 0].plot(xs, ys, c='dimgray')
    
    fig.patch.set_visible(False)
    ax[0, 0].axis('off')
    plt.tight_layout(pad=10)

    handles = []
    for i, p in enumerate(palette):
        handles.append(mpatches.Patch(color=palette[i, :], label='C'+str(i+1)))

    # plt.legend(handles=handles)
    ax[0, 0].legend(handles=handles, loc=(.6, .09), title='Communities',
                    fontsize='xx-large', title_fontsize='xx-large')

    extent = ax[0, 0].get_window_extent().transformed(fig.dpi_scale_trans.inverted())
    fig.savefig(pjoin(outdir, 'map_comm.pdf'), bbox_inches=extent.expanded(1.0, 1.0))
    fig.savefig(pjoin(outdir, 'map_comm.png'), bbox_inches=extent.expanded(1.0, 1.0))

##########################################################
def plot_proportion_per_cluster(clulabelspath, outdir):
    """Plot cluster labels.
    It expects a df with the points and corresponding cluster, objlabel
    and also a list of the areas of each cluster.
    """

    info(inspect.stack()[0][3] + '()')

    df = pd.read_csv(clulabelspath, index_col='id')
    totalrows = len(df)

    clusters = np.unique(df.cluster)
    clusters_str = ['c{}'.format(cl) for cl in clusters]
    nclusters = len(clusters)
    labels = np.unique(df.label)
    nlabels = len(labels)
    labelstr = [str(l) for l in labels]
    plotsize = 5

    colours = palette

    coloursrev = []
    for i in range(len(colours)):
        coloursrev.append(colours[len(colours) - 1 - i, :])

    # Plot by type
    fig, ax = plt.subplots(1, nlabels,
                           figsize=(nlabels*plotsize, .8*plotsize),
                           squeeze=False)

    clustersums = np.zeros((nclusters, nlabels))
    for i, cl in enumerate(clusters):
        aux = df[df.cluster == cl]
        for j, l in enumerate(labels):
            clustersums[i, j] = len(aux[aux.label == l])

    info('clustersums:{}'.format(np.sum(clustersums, axis=1)))
    
    labelsmap = {1: 'A', 2: 'B', 3: 'C'}
    for i, l in enumerate(labels):
        data = df[df.label == l]
        ys = np.zeros(nclusters)
        labelsum = len(data)
        for k, cl in enumerate(clusters):
            ys[k] = len(data[data.cluster == cl])

        barplot = ax[0, i].barh(list(reversed(clusters_str)), list(reversed(ys)),
                                color=coloursrev)
        # barplot = ax[0, i].barh(list(reversed(clusters_str)), list(reversed(ys)))
                                # color=coloursrev)

        # ax[0, i].set_xlim(0, 1)
        ax[0, i].set_title('Ratio of Type {} within communities'.\
                            format(r"$\bf{" + str(labelsmap[l]) + "}$"),
                           size='large', pad=30)
        # ax[0, i].xaxis.set_major_formatter(FormatStrFormatter('%.2f'))
        # ax[0, i].set_xticks([0, .25, 0.5, .75, 1.0])
        ax[0, i].spines['top'].set_color('gray')
        ax[0, i].xaxis.set_ticks_position('top')
        ax[0, i].tick_params(axis='x', which='both', length=0)
                    # , colors='gray', labelsize='large')
        ax[0, i].tick_params(axis='y', which='both', labelsize='large')
        ax[0, i].xaxis.grid(True, alpha=0.4)
        ax[0, i].set_axisbelow(True)
        ax[0, i].set_ylabel('Community')
        ax[0, i].xaxis.set_label_position('top')
        ax[0, i].set_xlabel('Graffiti type {} count'.format(l))

        def autolabel(rects, ys):
            for idx, rect in enumerate(rects):
                height = rect.get_height()
                delta = np.max(ys) / 20
                ax[0, i].text(rect.get_width() - delta,
                              rect.get_y() + rect.get_height()/2.-0.28,
                              '{}%'.format(int(ys[idx]/labelsum * 100)), color='white',
                              ha='center', va='bottom', rotation=0,)
                              # fontsize='large')

        autolabel(barplot, list(reversed(ys)))
        # ax[0, i].axis("off")
        for spine in ax[0, i].spines.values():
            spine.set_edgecolor('dimgray')
        ax[0, i].spines['bottom'].set_visible(False)
        ax[0, i].spines['right'].set_visible(False)
        ax[0, i].spines['left'].set_visible(False)

    plt.tight_layout(pad=5)
    export_individual_axis(ax, fig, labelstr, outdir, pad=0.5,
            prefix='bar_type', fmt='pdf')
    plt.savefig(pjoin(outdir, 'count_per_type.pdf'))

##########################################################
def plot_proportion_per_cluster2(clulabelspath, outdir):
    """Plot cluster labels.
    It expects a df with the points and corresponding cluster, objlabel
    and also a list of the areas of each cluster.
    """

    info(inspect.stack()[0][3] + '()')

    df = pd.read_csv(clulabelspath, index_col='id')
    totalrows = len(df)

    clusters = np.unique(df.cluster)
    clusters_str = ['c{}'.format(cl) for cl in clusters]
    nclusters = len(clusters)
    labels = np.unique(df.label)
    nlabels = len(labels)
    labelstr = [str(l) for l in labels]
    plotsize = 5

    data = {}
    for l in labels:
        data[str(l)] = df[df.label == l].groupby('cluster').sum()['label'].values
    
    df = pd.DataFrame.from_dict(data)
    
    df['community'] = df.index
    
    pd.plotting.parallel_coordinates(
        df, 'community',
        )
        # color=('#556270', '#4ECDC4', '#C7F464'))
    ax = plt.gca()
    ax.set_xlabel('Graffiti type')
    ax.set_ylabel('Number of occurrences')
    # ax.legend()
    # leg = ax.get_legend()
    breakpoint()
    
    plt.savefig('/tmp/parallel.png')


##########################################################
def plot_counts_normalized(clulabelspath, cluareaspath, outdir):
    df = pd.read_csv(clulabelspath, index_col='id')
    totalrows = len(df)

    clusters = np.unique(df.cluster)
    clusters_str = ['C{}'.format(cl) for cl in clusters]
    nclusters = len(clusters)
    labels = np.unique(df.label)
    nlabels = len(labels)
    # labels_str = [str(l) for l in labels]
    plotsize = 5
    alpha = 0.6
    palette = np.array([
        [27.0,158,119],
        [217,95,2],
        [117,112,179],
        [231,41,138],
        [102,166,30],
        [230,171,2],
    ])
    palette /= 255.0
    colours = np.zeros((palette.shape[0], 4), dtype=float)
    colours[:, :3] = palette
    colours[:, -1] = alpha

    counts = np.zeros(nclusters, dtype=int)
    countsnorm = np.zeros(nclusters)
    areas = pd.read_csv(cluareaspath)

    for i, cl in enumerate(clusters):
        data = df[df.cluster == cl]
        counts[i] = len(data)
        points = data[['x', 'y']].values

        countsnorm[i] = counts[i] / areas.iloc[i]

    fig, ax = plt.subplots(1, 1, figsize=(2*plotsize, plotsize),
                           squeeze=False)
    yfactor = 1
    ax[0, 0].bar(clusters_str, countsnorm / yfactor, color=colours)
    ax[0, 0].set_ylabel('Normalized count of graffitis')
    ax[0, 0].set_xlabel('Community')
    i = 0
    for spine in ax[0, i].spines.values():
        spine.set_edgecolor('dimgray')
    ax[0, i].ticklabel_format(axis="y", style="sci", scilimits=(0,0))
    ax[0, i].spines['top'].set_visible(False)
    ax[0, i].spines['right'].set_visible(False)
    ax[0, i].yaxis.grid(True, alpha=0.4)
    ax[0, i].set_axisbelow(True)
    # ax[0, i].spines['left'].set_visible(False)

    plt.savefig(pjoin(outdir, 'countsnormalized.pdf'))

##########################################################
def count_labels_per_region(df, clusters, labels, cluids):
    """Count number of labels per region
    """
    nlabels = len(labels)
    nclusters = len(clusters)

    counts = np.ones((nclusters, nlabels), dtype=float)
    for i in range(nclusters):
        labels_reg, counts_reg = np.unique(df[df.index.isin(cluids[i])].label,
                                           return_counts=True)
        for j in range(nlabels):
            lab = labels[j]
            if not lab in labels_reg: continue
            ind = np.where(labels_reg == lab)
            counts[i, j] = counts_reg[ind]
    return counts

##########################################################
def count_shuffled_labels_per_region(dforig, clusters, labels, cluids, nrealizations):
    """Shuffle and count for @nrealizations times
    Returns an array indexed by the nrealization, regionid, objtype
    """
    info(inspect.stack()[0][3] + '()')

    counts_perm = np.ones((nrealizations, len(clusters), len(labels)),
                             dtype=float) * 999

    for i in range(nrealizations):
        df = dforig.copy()
        newlabels = df.label.copy().values
        np.random.shuffle(newlabels)
        
        df['label'] = newlabels
        counts_perm[i, :, :] = count_labels_per_region(df, clusters, labels, cluids)
    return counts_perm

#############################################################
def shuffle_labels(labelspath, outdir):
    """Shuffle labels from @labelspath and compute metrics
    """
    info(inspect.stack()[0][3] + '()')
    df = pd.read_csv(labelspath, index_col='id')

    nrealizations = 10
    labels = np.unique(df.label)
    clusters = np.unique(df.cluster)
    nlabels = len(labels)
    nclusters = len(clusters)
    info('nrealizations:{}, nclusters:{}'.format(nrealizations, nclusters))

    cluids = {}
    for i in range(nclusters):
        # cluids[i] = df[df.cluster == clusters[i]].index
        cluids[i] = np.where(df.cluster.values == clusters[i])[0]

    counts_orig = count_labels_per_region(df, clusters, labels, cluids)
    counts_perm = count_shuffled_labels_per_region(df, clusters, labels,
            cluids, nrealizations)

    plot_shuffle_distrib_and_orig(counts_orig, counts_perm, nclusters,
            nlabels, outdir)

##########################################################
def plot_shuffle_distrib_and_orig(counts_orig, counts_perm, nclusters,
        nlabels, outdir):
    """Plot shuffle counts distribs and original counts """
    info(inspect.stack()[0][3] + '()')
    nperregion = np.sum(counts_orig, axis=1)
    plotsize = 5
    fig, ax = plt.subplots(1, nclusters,
                           figsize=(nclusters*plotsize, 1*plotsize),
                           squeeze=False)

    palette = np.array([
        [127,201,127, 255],
        [190,174,212, 255],
        [253,192,134, 255],
        [255,255,153, 255],
    ])
    palette = palette / 255

    for j in range(nclusters):
        for k in range(nlabels):
            data = counts_perm[:, j, k] / nperregion[j]
            density = stats.gaussian_kde(data)
            # density = gaussian_kde(data)
            xs = np.linspace(0, 1, num=100)
            density.covariance_factor = lambda : .25
            density._compute_covariance()
            ys = density(xs)
            ys /= np.sum(ys)
            ax[0, j].plot(xs, ys, label=str(k), c=palette[k])

            count_ref = counts_orig[j, k] / nperregion[j]
            ax[0, j].scatter(count_ref, 0, c=[palette[k]])
            plt.text(0.5, 0.9, 'samplesz:{:.0f}'.format(nperregion[j]),
                     horizontalalignment='center', verticalalignment='center',
                     fontsize='large', transform = ax[0, j].transAxes)


        ax[0, j].legend()
        ax[0, j].set_xlabel('Graffiti relative count')
    
    fig.suptitle('Distrubution of number of graffiti occurences '\
                    'per type (colours) and per cluster (plots)')

    print(nperregion)
    plt.savefig(pjoin(outdir, 'counts_shuffled_norm.pdf'))

##########################################################
def compile_lists(listsdir, labelspath):
    """Compile lists (.lst) in @listdir
    """
    info(inspect.stack()[0][3] + '()')
    files = sorted(os.listdir(listsdir))

    cols = 'img,x,y,label'.split(',')
    data = []
    for f in files:
        if not f.endswith('.lst'): continue
        label = int(f.replace('.lst', '').split('_')[1])
        lines = open(pjoin(listsdir, f)).read().strip().splitlines()
        for l in lines:
            id = l.replace('.jpg', '')
            _, y, x, heading = id.split('_')
            data.append([l, x, y, label])
    
    df = pd.DataFrame(data, columns=cols)
    df.to_csv(labelspath, index_label='id',)

#############################################################
def summarize_annotations(annotdir, labelspath):
    """Summarize @annotdir csv annotations in .txt format and output
    summary to @labelspath
    """
    info(inspect.stack()[0][3] + '()')
    files = sorted(os.listdir(annotdir))

    labels = '1 2 3'.split(' ')
    info('Using labels:{}'.format(labels))

    cols = 'img,x,y,label'.split(',')
    data = []
    for f in files:
        if not f.endswith('.txt'): continue
        filepath = pjoin(annotdir, f)
        _, y, x, heading = os.path.split(filepath)[-1].replace('.txt', '').split('_')
        labels_ = open(filepath).read().strip().split(',')

        for l in labels_: # each label in the file correspond to a new row
            img = f.replace('.txt', '.jpg')
            data.append([img, x, y, l])

    df = pd.DataFrame(data, columns=cols)
    df.to_csv(labelspath, index_label='id',)

##########################################################
def parse_infomap_output(graphmlpath, infomapout, labelspath, annotator, outpath):
    """Find enclosing community given by @infomapout of each node in @graphml
    """
    info(inspect.stack()[0][3] + '()')

    g = igraph.Graph.Read(graphmlpath)
    cludf = pd.read_csv(infomapout, sep=' ', skiprows=[0, 1],
                     names=['id', 'cluster','flow']) # load graph clusters
    cludf = cludf.sort_values(by=['id'], inplace=False)

    objsdf = pd.read_csv(labelspath, index_col='id') # load obj labels
    pd.set_option("display.precision", 8)

    coords_objs = np.zeros((len(objsdf), 2))
    
    i = 0
    for _, row in objsdf.iterrows():
        coords_objs[i, 0] = row.x
        coords_objs[i, 1] = row.y
        i += 1

    coords_nodes = np.array([g.vs['x'], g.vs['y']]).T

    kdtree = cKDTree(coords_nodes)
    dists, inds = kdtree.query(coords_objs)
    objsdf['cluster'] = np.array(cludf.cluster.tolist())[inds]
    objsdf['annotator'] = annotator
    objsdf.to_csv(outpath)

##########################################################
def convert_csv_to_annotdir(labelsclu, annotator, outdir):
    """Convert dataframe in @labelsclu from @annotator to txt format in @outdir
    """
    info(inspect.stack()[0][3] + '()')
    df = pd.read_csv(labelsclu)
    labels = np.unique(df.label)
    labeldir = pjoin(outdir, 'annot')
    if not os.path.isdir(labeldir): os.mkdir(labeldir)

    filtered = df[(df.annotator == annotator)]
    imgs = np.unique(filtered.img)

    for im in imgs:
        aux = filtered[filtered.img == im]
        mylabels = sorted(np.array(list(set(aux.label))).astype(str))
        if '1' in mylabels and len(mylabels) == 1: print(im)
        mylabelsstr = ','.join(mylabels)
        annotpath = pjoin(labeldir, im.replace('.jpg', '.txt'))
        open(pjoin(labeldir, annotpath), 'w').write(mylabelsstr)

##########################################################
def plot_venn(labelsclupath, outdir):
    """Plot venn diagram
    """
    info(inspect.stack()[0][3] + '()')
    df = pd.read_csv(labelsclupath)
    labels = sorted(np.unique(df.label))

    img2id = {}
    for i, img in enumerate(sorted(np.unique(df.img))):
        img2id[img] = i

    subsets = []
    for l in labels:
        aux = df[df.label == l].img.tolist()
        partition = [img2id[k] for k in aux]
        subsets.append(set(partition))

    edgecolours = ['#993333', '#339933', '#3366ff']
    matplotlib_venn.venn3(subsets,
            set_labels = ('TypeA', 'TypeB', 'TypeC'),
            set_colors=edgecolours,
            alpha=.7
            )
    plt.tight_layout()
    plt.savefig(pjoin(outdir, 'counts_venn.pdf'))


##########################################################
def main():
    info(inspect.stack()[0][3] + '()')
    t0 = time.time()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--outdir', default='/tmp/out/', help='Output directory')
    args = parser.parse_args()

    if not os.path.isdir(args.outdir): os.mkdir(args.outdir)

    annotdir = './data/20200202-types/20200209-8003_annot/'
    graphmlpath = './data/20200202-types/sp.graphml'
    clupath = './data/20200202-types/20200222-infomap.clu'
    shppath = './data/20200202-types/20200224-shp/'
    cluareaspath = './data/20200202-types/20200222-infomap_areas.csv'

    outlabels = pjoin(args.outdir, 'labels.csv')
    outlabelsclu = pjoin(args.outdir, 'labels_and_clu_nodupls.csv')
    annotator = 'er'

    # summarize_annotations(annotdir, outlabels)
    # parse_infomap_output(graphmlpath, clupath, outlabels,
            # annotator, outlabelsclu)
    # plot_types(clupath, shppath, outlabelsclu, args.outdir)
    # plot_communities(clupath, graphmlpath, shppath, args.outdir)
    plot_proportion_per_cluster2(outlabelsclu, args.outdir)
    # plot_counts_normalized(outlabelsclu, cluareaspath, args.outdir)
    # plot_venn(outlabelsclu, args.outdir)

    info('Elapsed time:{}'.format(time.time()-t0))

##########################################################
if __name__ == "__main__":
    main()

