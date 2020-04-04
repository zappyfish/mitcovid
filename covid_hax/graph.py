from query import *
import pandas as pd


class SessionResult:

    def __init__(self, conclusion, asked_questions, received_answers):
        self.conclusion = conclusion
        self.asked_questions = asked_questions
        self.received_answers = received_answers

def histogram_intersection(a, b):
    v = np.minimum(a, b).sum().round(decimals=1)
    return v

class ResultMatrix:

    def __init__(self, query_nodes):
        cnt = 0
        self.key_index_map = {}
        for node in query_nodes:
            for answer in node.answers:
                key = self.get_question_answer_key(node.question, answer)
                self.key_index_map[key] = cnt
                cnt += 1
        self.data = [[0 for i in range(cnt)] for j in range(cnt)]

    def add_entry_and_related(self, question, answer, related_questions, related_answers):
        key = self.get_question_answer_key(question.question, answer.answer)
        i1 = self.key_index_map[key]
        n = len(related_questions)
        for i in range(n):
            related_key = self.get_question_answer_key(related_questions[i].question, related_answers[i].answer)
            assert related_questions[i].question != question.question
            i2 = self.key_index_map[related_key]
            self.data[i1][i2] += 1

    def update_matrix(self, questions, answers):
        assert len(questions) == len(answers)
        n = len(questions)
        for i in range(n):
            q = questions.pop(0)
            a = answers.pop(0)
            self.add_entry_and_related(q, a, questions, answers)
            questions.append(q)
            answers.append(a)

    def show_correlation_matrix(self):
        df = pd.DataFrame(self.data, columns=[k for k in self.key_index_map])
        corr = df.corr(method=histogram_intersection)
        print(corr)

    def correlate_between_answer_and_questions(self, question, next_node_and_correlation):
        question_and_correlation = {}
        for node in next_node_and_correlation:
            q_name = node.split("|")[0]
            if q_name == question:
                continue
            if q_name not in question_and_correlation:
                question_and_correlation[q_name] = []
            question_and_correlation[q_name].append(next_node_and_correlation[node])
        tot = 0
        for node in question_and_correlation:
            question_and_correlation[node] = np.var(question_and_correlation[node])
            tot += question_and_correlation[node]  # Compute variance
        for node in question_and_correlation:
            question_and_correlation[node] /= tot  # Normalize
        return question_and_correlation

    def get_correlation(self):
        df = pd.DataFrame(self.data, columns=[k for k in self.key_index_map])
        corr = df.corr(method=histogram_intersection)
        names = [row for row in corr]
        results = {}
        for row in corr:
            question = row.split("|")[0]
            answer = row.split("|")[1]
            values = corr[row]
            next_node_and_correlation = {name: values[name] for name in names}
            if question not in results:
                results[question] = {}
            results[question][answer] = self.correlate_between_answer_and_questions(question, next_node_and_correlation)
        return results

    @staticmethod
    def get_question_answer_key(question, answer):
        return question + "|" + answer


class SessionResults:

    def __init__(self, query_nodes, conclusions):
        self.results = []
        self.result_matrices = {conc: ResultMatrix(query_nodes) for conc in conclusions}


    def add_result(self, result):
        self.results.append(result)
        self.update_correlation(self.result_matrices[result.conclusion], result.asked_questions, result.received_answers)

    def update_correlation(self, matrix, questions, answers):
        matrix.update_matrix(questions, answers)


class QuerySession:

    def __init__(self, graph, desired_conclusion=None):
        self.conclusion = desired_conclusion
        self.graph = graph
        self.graph.build_graph(desired_conclusion)
        self.asked_questions = []
        self.received_answers = []
        self.current_query = self.get_next_question(self.graph.root.answers["root"])

    def get_next_question(self, answer):
        return answer.pick_next_question(self.asked_questions)

    def receive_answer_for_next_question(self, answer):
        answer_node = self.current_query.answers[answer]
        assert self.current_query not in self.asked_questions
        self.asked_questions.append(self.current_query)
        self.received_answers.append(answer_node)
        last_q = self.current_query
        self.current_query = self.get_next_question(answer_node)
        assert self.current_query not in self.asked_questions
        assert last_q != self.current_query
        return self.current_query

    def get_session_result(self):
        return SessionResult(self.conclusion, self.asked_questions, self.received_answers)


class QueryGraph:

    def __init__(self, nodes):
        self.root = QueryNode("root")
        self.query_nodes = nodes  # List[QueryNode]

    def build_graph(self, conclusion=None):
        self.attach_to_root(conclusion)

    def attach_to_root(self, conclusion=None):
        root_answer = AnswerNode("root")
        for node in self.query_nodes:
            root_answer.next_questions[node] = node.relevance(conclusion)
        self.root.answers["root"] = root_answer
