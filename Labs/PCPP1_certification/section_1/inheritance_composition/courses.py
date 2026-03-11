class Subject:
    def __init__(self, name):
        self.name = name
    

class Course:
    def __init__(self, name, subject):
        self.name = name
        self.subject = subject

    def course_info(self):
        return f"The course '{self.name}' is about {self.subject.name}."
    
class MathCourse(Course):
    def __init__(self, name, subject, level):
        super().__init__(name, subject)
        self.level = level

    def course_info(self):
        base_info = super().course_info()
        return f"{base_info} It is a {self.level} level course."

class ScienceCourse(Course):
    def __init__(self, name, subject, lab_required):
        super().__init__(name, subject)
        self.lab_required = lab_required

    def course_info(self):
        base_info = super().course_info()
        lab_info = "requires a lab" if self.lab_required else "does not require a lab"
        return f"{base_info} It {lab_info}."
    
class HistoryCourse(Course):
    def __init__(self, name, subject, era):
        super().__init__(name, subject)
        self.era = era

    def course_info(self):
        base_info = super().course_info()
        return f"{base_info} It focuses on the {self.era} era."
    
class LiteratureCourse(Course):
    def __init__(self, name, subject, author):
        super().__init__(name, subject)
        self.author = author

    def course_info(self):
        base_info = super().course_info()
        return f"{base_info} It studies the works of {self.author}."
    
class ArtCourse(Course):
    def __init__(self, name, subject, medium):
        super().__init__(name, subject)
        self.medium = medium

    def course_info(self):
        base_info = super().course_info()
        return f"{base_info} It focuses on {self.medium} art."
    
class MusicCourse(Course):
    def __init__(self, name, subject, instrument):
        super().__init__(name, subject)
        self.instrument = instrument

    def course_info(self):
        base_info = super().course_info()
        return f"{base_info} It teaches how to play the {self.instrument}."
    
class ComputerScienceCourse(Course):
    def __init__(self, name, subject, programming_language):
        super().__init__(name, subject)
        self.programming_language = programming_language

    def course_info(self):
        base_info = super().course_info()
        return f"{base_info} It focuses on programming in {self.programming_language}."
    
class PhysicalEducationCourse(Course):
    def __init__(self, name, subject, sport):
        super().__init__(name, subject)
        self.sport = sport

    def course_info(self):
        base_info = super().course_info()
        return f"{base_info} It involves playing {self.sport}."
    
class LanguageCourse(Course):
    def __init__(self, name, subject, language):
        super().__init__(name, subject)
        self.language = language

    def course_info(self):
        base_info = super().course_info()
        return f"{base_info} It teaches the {self.language} language."
    

    
class OnlineCourse(Course):
    def __init__(self, name, subject, platform):
        super().__init__(name, subject)
        self.platform = platform

    def course_info(self):
        base_info = super().course_info()
        return f"{base_info} It is available on {self.platform}."
    
class OfflineCourse(Course):
    def __init__(self, name, subject, location):
        super().__init__(name, subject)
        self.location = location

    def course_info(self):
        base_info = super().course_info()
        return f"{base_info} It is held at {self.location}."

