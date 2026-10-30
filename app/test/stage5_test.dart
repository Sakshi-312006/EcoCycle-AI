import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ecocycle_ai/core/app_state.dart';
import 'package:ecocycle_ai/screens/cd_material_details_screen.dart';
import 'package:ecocycle_ai/screens/cd_waste_screen.dart';
import 'package:ecocycle_ai/screens/purchase_cd_material_screen.dart';
import 'package:ecocycle_ai/screens/report_cd_debris_screen.dart';
import 'package:ecocycle_ai/screens/sell_cd_material_screen.dart';

void main() {
  testWidgets('Screen 8: Construction Debris Hub renders heading, 3 primary actions & future scope',
      (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);

    final appState = AppState();
    await tester.pumpWidget(MaterialApp(
      home: CDWasteScreen(appState: appState),
    ));

    // Verify Title and Subtitle
    expect(find.text('Construction Debris'), findsOneWidget);
    expect(find.text('Manage construction waste responsibly'), findsOneWidget);

    // Verify 3 Primary Actions
    expect(find.text('Report Debris'), findsOneWidget);
    expect(find.text('Sell Materials'), findsOneWidget);
    expect(find.text('Purchase Materials'), findsOneWidget);

    // Verify Statutory Guidelines
    expect(find.text('C&D Waste Management Rules, 2016'), findsOneWidget);
    expect(find.textContaining('Segregate debris into concrete, masonry'), findsOneWidget);

    // Verify Future Scope Section
    expect(find.text('FUTURE SCOPE'), findsOneWidget);
    expect(find.text('AI-Based Vehicle Selection'), findsOneWidget);
    expect(find.text('Camera-Based Government Vehicle Monitoring'), findsOneWidget);
    expect(find.text('Automatic Vehicle Assignment'), findsOneWidget);
  });

  testWidgets('Screen 8: Navigation to Report Debris, Sell Materials & Purchase Materials',
      (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);

    final appState = AppState();
    await tester.pumpWidget(MaterialApp(
      home: CDWasteScreen(appState: appState),
    ));

    // Tap Report Debris
    await tester.tap(find.text('Report Debris'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));
    expect(find.byType(ReportCDDebrisScreen), findsOneWidget);
    expect(find.text('Report Construction Debris'), findsOneWidget);

    // Go back
    await tester.tap(find.byIcon(Icons.arrow_back_ios_new_rounded));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    // Tap Sell Materials (Screen 9)
    await tester.tap(find.text('Sell Materials'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));
    expect(find.byType(SellCDMaterialScreen), findsOneWidget);
    expect(find.text('Sell Construction Material'), findsOneWidget);

    // Go back
    await tester.tap(find.byIcon(Icons.arrow_back_ios_new_rounded));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    // Tap Purchase Materials (Screen 10)
    await tester.tap(find.text('Purchase Materials'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));
    expect(find.byType(PurchaseCDMaterialScreen), findsOneWidget);
    expect(find.text('Construction Materials'), findsOneWidget);
  });

  testWidgets('Screen 9: Sell Construction Material form validation and fields',
      (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);

    final appState = AppState();
    await tester.pumpWidget(MaterialApp(
      home: SellCDMaterialScreen(appState: appState),
    ));

    expect(find.text('Sell Construction Material'), findsOneWidget);
    expect(find.text('Listing Title'), findsOneWidget);
    expect(find.text('Category'), findsOneWidget);
    expect(find.text('Quantity'), findsOneWidget);
    expect(find.text('Condition'), findsOneWidget);
    expect(find.text('Price in INR (₹)'), findsOneWidget);
    expect(find.text('Pickup Site Address'), findsOneWidget);
    expect(find.text('List Material for Sale'), findsOneWidget);
  });

  testWidgets('Screen 10: Purchase Construction Material renders filters and catalog',
      (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);

    final appState = AppState();
    await tester.pumpWidget(MaterialApp(
      home: PurchaseCDMaterialScreen(appState: appState),
    ));
    await tester.pump();

    expect(find.text('Construction Materials'), findsOneWidget);
    expect(find.text('Search bricks, cement, steel, timber...'), findsOneWidget);

    // Verify filter pills
    expect(find.text('All'), findsOneWidget);
    expect(find.text('Bricks'), findsWidgets);
    expect(find.text('Cement'), findsOneWidget);
    expect(find.text('Steel'), findsOneWidget);

    // Verify catalog items from Screen 10 reference
    expect(find.text('Cement Bags'), findsOneWidget);
    expect(find.text('Steel Rods (TMT)'), findsOneWidget);
    expect(find.text('Wooden Planks'), findsOneWidget);
  });

  testWidgets('Screen 11: Material Details displays info and handles Buy Now and Contact Seller',
      (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);

    final appState = AppState();
    final sampleItem = {
      'id': 'test-bricks',
      'title': 'Bricks',
      'category': 'Bricks',
      'condition': 'Good condition',
      'quantity': '500 pcs',
      'price': '₹8 per piece',
      'location': 'Demolition Site A',
      'sellerName': 'Ramesh Kumar',
      'rating': '4.8 (12 reviews)',
      'description': 'High quality red bricks, suitable for general construction.',
      'color': const Color(0xFF8D6E63),
      'icon': Icons.handyman_rounded,
    };

    await tester.pumpWidget(MaterialApp(
      home: CDMaterialDetailsScreen(
        appState: appState,
        referenceMaterial: sampleItem,
      ),
    ));

    expect(find.text('Construction Material'), findsOneWidget);
    expect(find.text('Bricks'), findsOneWidget);
    expect(find.text('Good condition • 500 pcs'), findsOneWidget);
    expect(find.text('₹8 per piece'), findsOneWidget);
    expect(find.text('Ramesh Kumar'), findsOneWidget);
    expect(find.text('Contact Seller'), findsOneWidget);
    expect(find.text('Buy Now'), findsOneWidget);

    // Tap Contact Seller
    await tester.tap(find.text('Contact Seller'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));
    expect(find.text('Contact Ramesh Kumar'), findsOneWidget);
    expect(find.text('Call Site Coordinator'), findsOneWidget);

    // Dismiss bottom sheet
    await tester.tap(find.text('Call Site Coordinator'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    // Tap Buy Now
    await tester.tap(find.text('Buy Now'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));
    expect(find.text('Material Reserved!'), findsOneWidget);
  });

  testWidgets('ReportCDDebrisScreen: Rule-based vehicle recommendation logic',
      (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);

    final appState = AppState();
    await tester.pumpWidget(MaterialApp(
      home: ReportCDDebrisScreen(appState: appState),
    ));

    // By default, dimensions are 2.5 x 1.5 x 0.8 = 3.0 m3. Density is 1.5 t/m3 => 4.5 Tonnes.
    // 4.5 Tonnes falls into TIPPER-TRUCK-05 (1.0T to 5.0T).
    expect(find.textContaining('TIPPER-TRUCK-05'), findsWidgets);
    expect(find.text('Recommended Vehicle'), findsOneWidget);
    expect(find.text('Rule-Based Route Decision Engine'), findsOneWidget);
  });
}
