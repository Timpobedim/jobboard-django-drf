from jobboard.apps.core.renderers import JobBoardJSONRenderer


class UserJSONRenderer(JobBoardJSONRenderer):
    object_label = "user"
