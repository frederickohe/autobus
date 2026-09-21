import unittest

from core.media.service.video_concat import build_filter_graph, output_size


class VideoConcatHelpersTest(unittest.TestCase):
    def test_portrait_output_size(self):
        self.assertEqual(output_size("9:16"), (720, 1280))
        self.assertEqual(output_size("16:9"), (1280, 720))

    def test_filter_graph_video_only(self):
        graph = build_filter_graph(2, 1280, 720, False)
        self.assertIn("concat=n=2:v=1:a=0[vout]", graph)
        self.assertNotIn("[aout]", graph)
        self.assertIn("[0:v]scale=1280:720", graph)

    def test_filter_graph_with_audio(self):
        graph = build_filter_graph(3, 720, 1280, True)
        self.assertIn("concat=n=3:v=1:a=1[vout][aout]", graph)
        self.assertIn("[2:a]aresample=44100", graph)


if __name__ == "__main__":
    unittest.main()
