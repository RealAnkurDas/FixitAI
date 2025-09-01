import 'package:cloud_firestore/cloud_firestore.dart';

class PostModel {
  final String id;
  final String userId;
  final String title;
  final String description;
  final String? imageURL;
  final String deviceType;
  final String difficulty;
  final int timeRequired; // in minutes
  final List<String> toolsUsed;
  final List<String> tags;
  final int likesCount;
  final int commentsCount;
  final List<String> likedBy;
  final List<String> savedBy;
  final DateTime createdAt;
  final DateTime? updatedAt;

  PostModel({
    required this.id,
    required this.userId,
    required this.title,
    required this.description,
    this.imageURL,
    required this.deviceType,
    required this.difficulty,
    required this.timeRequired,
    required this.toolsUsed,
    required this.tags,
    this.likesCount = 0,
    this.commentsCount = 0,
    this.likedBy = const [],
    this.savedBy = const [],
    required this.createdAt,
    this.updatedAt,
  });

  Map<String, dynamic> toMap() {
    return {
      'id': id,
      'userId': userId,
      'title': title,
      'description': description,
      'imageURL': imageURL,
      'deviceType': deviceType,
      'difficulty': difficulty,
      'timeRequired': timeRequired,
      'toolsUsed': toolsUsed,
      'tags': tags,
      'likesCount': likesCount,
      'commentsCount': commentsCount,
      'likedBy': likedBy,
      'savedBy': savedBy,
      'createdAt': Timestamp.fromDate(createdAt),
      'updatedAt': updatedAt != null ? Timestamp.fromDate(updatedAt!) : null,
    };
  }

  factory PostModel.fromMap(Map<String, dynamic> map) {
    return PostModel(
      id: map['id'] ?? '',
      userId: map['userId'] ?? '',
      title: map['title'] ?? '',
      description: map['description'] ?? '',
      imageURL: map['imageURL'],
      deviceType: map['deviceType'] ?? '',
      difficulty: map['difficulty'] ?? '',
      timeRequired: map['timeRequired']?.toInt() ?? 0,
      toolsUsed: List<String>.from(map['toolsUsed'] ?? []),
      tags: List<String>.from(map['tags'] ?? []),
      likesCount: map['likesCount']?.toInt() ?? 0,
      commentsCount: map['commentsCount']?.toInt() ?? 0,
      likedBy: List<String>.from(map['likedBy'] ?? []),
      savedBy: List<String>.from(map['savedBy'] ?? []),
      createdAt: map['createdAt'] != null 
          ? (map['createdAt'] as Timestamp).toDate() 
          : DateTime.now(),
      updatedAt: map['updatedAt'] != null 
          ? (map['updatedAt'] as Timestamp).toDate() 
          : null,
    );
  }

  PostModel copyWith({
    String? id,
    String? userId,
    String? title,
    String? description,
    String? imageURL,
    String? deviceType,
    String? difficulty,
    int? timeRequired,
    List<String>? toolsUsed,
    List<String>? tags,
    int? likesCount,
    int? commentsCount,
    List<String>? likedBy,
    List<String>? savedBy,
    DateTime? createdAt,
    DateTime? updatedAt,
  }) {
    return PostModel(
      id: id ?? this.id,
      userId: userId ?? this.userId,
      title: title ?? this.title,
      description: description ?? this.description,
      imageURL: imageURL ?? this.imageURL,
      deviceType: deviceType ?? this.deviceType,
      difficulty: difficulty ?? this.difficulty,
      timeRequired: timeRequired ?? this.timeRequired,
      toolsUsed: toolsUsed ?? this.toolsUsed,
      tags: tags ?? this.tags,
      likesCount: likesCount ?? this.likesCount,
      commentsCount: commentsCount ?? this.commentsCount,
      likedBy: likedBy ?? this.likedBy,
      savedBy: savedBy ?? this.savedBy,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
    );
  }
}
