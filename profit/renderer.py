color_map = {range(0,10) : "#1d2559", range(10,20) : "#203078",
             range(20,30) : "#1f3b98", range(30,40) : "#1946ba",
             range(40,50) : "#5661c6", range(50,60) : "#7d7fd2",
             range(60,70) : "#a09dde", range(70,80) : "#c0bde9",
             range(80,90) : "#e0ddf4", range(90,101) : "#ffffff"}
from observer_abc import Observer
import graphviz as gv
import os

DECORATE = False

def _decorate_label(label, sep='_', max_len=15):
    """Text wrapping to the next line by sep."""
    if not DECORATE: return label
    new_label = ''
    beg = 0
    while label:
        id_sep = label.find(sep, beg)
        if (len(label[:id_sep]) > max_len) & (id_sep != -1):
            new_label += label[:id_sep] + '\n'
            label = label[id_sep+1:]
            beg = 0
        elif (id_sep == -1):
            new_label += label
            label = ''
        else:
            beg += id_sep + 1
    return new_label

class Renderer(Observer):
    """Class to represent the visualization of a process model."""

    def __init__(self):
        """GV attribute (default None) represents dot format (directed) graph 
        object that can be rendered with the Graphviz installation."""
        self.GV = None

    def update(self, TM, G, timenetwork=None, context=False, colored=True, render_format='png'):
        """Update graph object (GV attribute) and its representation: elements 
        count, node color, edge thickness, etc.

        Parameters
        ----------
        TM: TransitionMatrix
            A matrix describing the transitions of a Markov chain
        G: Graph
            Graph structure of the model
        colored: bool
            Whether represent graph elements in color or in black
            and white (default True)

        References
        ----------
        .. [1] Ferreira, D. R. (2017). A primer on process mining. Springer, Cham.
        """
        T, nodes, edges = TM.T, G.nodes, G.edges
        G = gv.Digraph(strict=False, format=render_format)
        G.attr('edge', fontname='Sans Not-Rotated 14')
        G.attr('node', shape='box', style='filled', fontname='Sans Not-Rotated 14')
        
        # 1. Node color and shape
        F = dict() # Activities absolute frequencies
        for a, a_freq in nodes.items():
            if type(a_freq[-1]) == dict:
                vals = [v for v in a_freq[-1].values()]
                F[a] = sum(vals) / len(vals)
            else:
                F[a] = a_freq[0]
        case_cnt = sum([v[0] for v in T['start'].values()])
        x_max, x_min = max(F.values()), min(F.values())
        for a, a_freq in nodes.items():
            color = int((x_max - F[a]) / (x_max - x_min + 1e-6) * 100.)
            fill, font = "#ffffff", 'black'
            if colored:
                for interval in color_map:
                    if color in interval:
                        fill = color_map[interval]
                        break
            else: fill = 'gray' + str(color)
            if color < 50:
                font = 'white'
            if type(a) == tuple:
                if type(a_freq[-1]) == dict:
                    add_counts = [' ('+str(a_freq[-1][c])+')' for c in a]
                else: add_counts = [''] * len(a)
                node_label = str(a[0]) + add_counts[0]
                for i in range(1, len(a)):
                    node_label += '\n' + str(a[i]) + add_counts[i]
                node_label += '\n(' + str(a_freq[0]) + ')'
                G.node(str(a), label=node_label, fillcolor=fill, fontcolor=font, shape='octagon')
            else:
                node_label = _decorate_label(str(a)) + '\n(' + str(F[a]) + ')'
                G.node(str(a), label=node_label, fillcolor=fill, fontcolor=font)
        G.node("start", shape="circle", label=str(case_cnt),
               fillcolor="#95d600" if colored else "#ffffff", margin='0.05')
        G.node("end", shape="doublecircle", label='',
               fillcolor="#ea4126" if colored else "#ffffff")
        
        # 2. Edge thickness and style
        if timenetwork is not None:
            # Create dictionary mapping (source,target) tuples to avg execution times
            time_dict = {}
            if context: context_dict = {}
            for _, row in timenetwork.iterrows():
                time_dict[(row['source'], row['target'])] = row['avg_execution_time_seconds']
                if context: context_dict[(row['source'], row['target'])] = row['context']

            # Filter time_dict to only keep entries where the edge exists in edges
            time_dict = {k: v for k, v in time_dict.items() if k in edges}
            values = list(time_dict.values())

            if values: t_min, t_max = min(values), max(values)
            
            for e, freq in edges.items():
                if (e[0], e[1]) in time_dict:
                    t = time_dict[(e[0], e[1])]
                if freq == (0, 0):
                    G.edge(str(e[0]), str(e[1]), style='dotted')
                    continue
                if (e[0] == 'start') | (e[1] == 'end'):
                    G.edge(str(e[0]), str(e[1]), style='dashed')
                else:
                    y = 1.0 + (5.0 - 1.0) * (t - t_min) / (t_max - t_min + 1e-6)

                    # Convert seconds to days, hours, minutes, seconds
                    days = int(t // (24 * 3600))
                    remaining = t % (24 * 3600)
                    hours = int(remaining // 3600)
                    remaining = remaining % 3600
                    minutes = int(remaining // 60)
                    seconds = int(remaining % 60)
                    
                    # Format time string
                    time_str = ""
                    if days > 0:
                        time_str += f"{days}d "
                    if hours > 0:
                        time_str += f"{hours}h "
                    if minutes > 0:
                        time_str += f"{minutes}m "
                    if seconds > 0 or time_str == "":
                        time_str += f"{seconds}s"

                    if context and (e[0], e[1]) in context_dict: label = context_dict[(e[0], e[1])] + " : " + time_str
                    else: label = time_str
                    
                    G.edge(str(e[0]), str(e[1]), label=label.strip(), penwidth=str(y))
        else:
            values = [freq[0] for freq in edges.values()]
            if values: t_min, t_max = min(values), max(values)
            for e, freq in edges.items():
                if freq == (0, 0):
                    G.edge(str(e[0]), str(e[1]), style='dotted')
                    continue
                if (e[0] == 'start') | (e[1] == 'end'):
                    G.edge(str(e[0]), str(e[1]), label=str(freq[0]), style='dashed')
                else:
                    y = 1.0 + (5.0 - 1.0) * (freq[0] - t_min) / (t_max - t_min + 1e-6)
                    G.edge(str(e[0]), str(e[1]), label=str(freq[0]), penwidth=str(y))
        
        self.GV = G

    def show(self):
        """Show graph without saving."""
        self.GV.view('tmp_view')
        os.system("pause")
        for fname in os.listdir():
            if fname.startswith("tmp_view"):
                os.remove(fname)
        return

    def save(self, save_path=None, gv_format_save=False):
        """Render and save graph in PNG (GV) format in the working directory,
        if no path to specific directory was indicated in save_path.
        """
        if save_path is None:
            save_path = os.path.dirname(os.path.abspath(__file__))
        if os.path.isdir(save_path):
        	save_name = input("Enter file name: ")
        	save_path = save_path + save_name        
        self.GV.render(save_path, view=False)
        if not gv_format_save:
            os.remove(save_path)
